"""
AUTOMATED REPORT SCHEDULER
Sends daily quantitative trading reports at frequent intervals via email

Features:
- Configurable interval (default: every 4 hours)
- Automatic retry on failure
- Background execution
- Detailed logging
- Manual trigger option
"""

import schedule
import time
import subprocess
import sys
from datetime import datetime
import logging
import os

# =============================================================================
# CONFIGURATION
# =============================================================================

# Report intervals - Choose your frequency
REPORT_INTERVALS = [
    "06:00",  # 6 AM - Pre-market analysis
    "10:00",  # 10 AM - Morning session review
    "14:00",  # 2 PM - Midday update
    "18:00",  # 6 PM - Evening session review
    "22:00"   # 10 PM - End of day summary
]

# Or use continuous interval (uncomment to use instead of fixed times)
# CONTINUOUS_INTERVAL_HOURS = 4  # Run every 4 hours

# Report script path
REPORT_SCRIPT = "exhaustive_daily_quant_report.py"

# Enable/disable specific features
SEND_EMAIL = True
SAVE_LOCAL = True
RETRY_ON_FAILURE = True
MAX_RETRIES = 3

# Logging
LOG_FILE = "report_scheduler.log"
LOG_LEVEL = logging.INFO

# =============================================================================
# LOGGING SETUP
# =============================================================================

logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# =============================================================================
# REPORT EXECUTION
# =============================================================================

def run_report_with_retry():
    """Run the report script with retry logic"""
    attempt = 0
    max_attempts = MAX_RETRIES if RETRY_ON_FAILURE else 1

    while attempt < max_attempts:
        attempt += 1
        logger.info(f"{'='*80}")
        logger.info(f"EXECUTING DAILY REPORT - Attempt {attempt}/{max_attempts}")
        logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"{'='*80}")

        try:
            # Run the report script
            result = subprocess.run(
                [sys.executable, REPORT_SCRIPT],
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )

            if result.returncode == 0:
                logger.info("✅ Report generated successfully!")
                logger.info(f"Output:\n{result.stdout}")
                return True
            else:
                logger.error(f"❌ Report generation failed (Exit code: {result.returncode})")
                logger.error(f"Error output:\n{result.stderr}")

                if attempt < max_attempts:
                    wait_time = 30 * attempt  # Exponential backoff
                    logger.info(f"⏳ Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"❌ Max retries ({max_attempts}) reached. Giving up.")
                    return False

        except subprocess.TimeoutExpired:
            logger.error(f"❌ Report script timed out after 10 minutes")

            if attempt < max_attempts:
                logger.info(f"⏳ Retrying...")
            else:
                logger.error(f"❌ Max retries reached after timeout.")
                return False

        except Exception as e:
            logger.error(f"❌ Unexpected error: {str(e)}")

            if attempt < max_attempts:
                logger.info(f"⏳ Retrying...")
            else:
                logger.error(f"❌ Max retries reached after error.")
                return False

    return False


def scheduled_report_job():
    """Job function called by scheduler"""
    logger.info(f"\n{'#'*80}")
    logger.info(f"# SCHEDULED REPORT TRIGGER")
    logger.info(f"# {datetime.now().strftime('%A, %B %d, %Y - %I:%M %p')}")
    logger.info(f"{'#'*80}\n")

    success = run_report_with_retry()

    if success:
        logger.info(f"\n{'='*80}")
        logger.info("✅ SCHEDULED REPORT COMPLETED SUCCESSFULLY")
        logger.info(f"{'='*80}\n")
    else:
        logger.error(f"\n{'='*80}")
        logger.error("❌ SCHEDULED REPORT FAILED")
        logger.error(f"{'='*80}\n")

    # Print next scheduled run
    next_run = schedule.next_run()
    if next_run:
        logger.info(f"⏰ Next report scheduled for: {next_run.strftime('%Y-%m-%d %H:%M:%S')}\n")


# =============================================================================
# SCHEDULER SETUP
# =============================================================================

def setup_scheduler():
    """Setup the scheduler with configured intervals"""
    logger.info(f"\n{'='*80}")
    logger.info("AUTOMATED REPORT SCHEDULER - INITIALIZING")
    logger.info(f"{'='*80}\n")

    # Check if report script exists
    if not os.path.exists(REPORT_SCRIPT):
        logger.error(f"❌ ERROR: Report script not found: {REPORT_SCRIPT}")
        logger.error("Please ensure 'exhaustive_daily_quant_report.py' is in the same directory.")
        sys.exit(1)

    # Setup scheduled times
    if 'CONTINUOUS_INTERVAL_HOURS' in globals():
        # Continuous interval mode
        schedule.every(CONTINUOUS_INTERVAL_HOURS).hours.do(scheduled_report_job)
        logger.info(f"✅ Scheduler configured: Every {CONTINUOUS_INTERVAL_HOURS} hours")
        logger.info(f"   First report will run in {CONTINUOUS_INTERVAL_HOURS} hours from now")
    else:
        # Fixed times mode
        for report_time in REPORT_INTERVALS:
            schedule.every().day.at(report_time).do(scheduled_report_job)
            logger.info(f"✅ Scheduled: Daily at {report_time}")

    logger.info(f"\n📧 Email delivery: {'ENABLED' if SEND_EMAIL else 'DISABLED'}")
    logger.info(f"💾 Local save: {'ENABLED' if SAVE_LOCAL else 'DISABLED'}")
    logger.info(f"🔄 Auto-retry: {'ENABLED ({} retries)'.format(MAX_RETRIES) if RETRY_ON_FAILURE else 'DISABLED'}")
    logger.info(f"📝 Log file: {LOG_FILE}")

    # Show next scheduled run
    next_run = schedule.next_run()
    if next_run:
        logger.info(f"\n⏰ Next report scheduled for: {next_run.strftime('%A, %B %d, %Y at %I:%M %p')}")

    logger.info(f"\n{'='*80}")
    logger.info("SCHEDULER ACTIVE - Running in background")
    logger.info("Press Ctrl+C to stop")
    logger.info(f"{'='*80}\n")


# =============================================================================
# MANUAL TRIGGER
# =============================================================================

def run_report_now():
    """Manually trigger report generation"""
    logger.info("\n🎯 MANUAL REPORT TRIGGER\n")
    scheduled_report_job()


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main execution loop"""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    AUTOMATED DAILY REPORT SCHEDULER                          ║
║                  Professional Trading Intelligence System                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)

    # Setup scheduler
    setup_scheduler()

    # Ask if user wants to run report immediately
    print("\n" + "="*80)
    print("OPTIONS:")
    print("  1. Wait for next scheduled time")
    print("  2. Run report NOW and then continue scheduled runs")
    print("="*80)

    try:
        choice = input("\nEnter choice (1 or 2, default=1): ").strip()

        if choice == "2":
            print("\n🚀 Running report immediately...\n")
            run_report_now()
        else:
            print("\n⏰ Waiting for next scheduled time...\n")

    except KeyboardInterrupt:
        print("\n\n⚠️  Using default: Wait for scheduled time\n")

    # Main scheduler loop
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

    except KeyboardInterrupt:
        logger.info("\n\n" + "="*80)
        logger.info("🛑 SCHEDULER STOPPED BY USER")
        logger.info("="*80)
        logger.info("All scheduled reports have been cancelled.")
        logger.info("To resume, run this script again.\n")

    except Exception as e:
        logger.error(f"\n❌ FATAL ERROR: {str(e)}")
        logger.error("Scheduler has stopped unexpectedly.")
        sys.exit(1)


if __name__ == "__main__":
    main()
