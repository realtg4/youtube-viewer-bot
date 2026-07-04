#!/usr/bin/env python3
"""
Main entry point for YouTube viewer bot
Supports both regular videos and live streams
Designed for 24/7 hosting on platforms like bot-hosting.net
"""

import asyncio
import os
import sys
import signal
import logging
import random
from datetime import datetime
from live_stream_viewer import MultiViewerManager, LiveStreamViewer
from youtube_viewer import YouTubeViewer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('viewer_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

class PersistentViewerBot:
    def __init__(self):
        self.manager = None
        self.is_running = False
        self.restart_count = 0
        
        # Configuration - EDIT THESE VALUES
        self.STREAM_URL = os.getenv('STREAM_URL', "https://www.youtube.com/watch?v=YOUR_STREAM_ID")
        self.VIDEO_URLS = os.getenv('VIDEO_URLS', "").split(',') if os.getenv('VIDEO_URLS') else []
        self.BOT_MODE = os.getenv('BOT_MODE', 'LIVE').upper()  # LIVE, VIDEO, or MIXED
        self.VIEWER_COUNT = int(os.getenv('VIEWER_COUNT', '5'))
        self.MAX_DURATION_MINUTES = int(os.getenv('MAX_DURATION_MINUTES', '0')) or None  # 0 = unlimited
        self.RESTART_INTERVAL_HOURS = int(os.getenv('RESTART_INTERVAL_HOURS', '6'))  # Restart every 6 hours
        
        # Clean up video URLs
        self.VIDEO_URLS = [url.strip() for url in self.VIDEO_URLS if url.strip()]
        
        logging.info(f"Bot configured:")
        logging.info(f"  Mode: {self.BOT_MODE}")
        logging.info(f"  Stream URL: {self.STREAM_URL}")
        logging.info(f"  Video URLs: {len(self.VIDEO_URLS)} videos")
        logging.info(f"  Viewer Count: {self.VIEWER_COUNT}")
        logging.info(f"  Max Duration: {self.MAX_DURATION_MINUTES or 'Unlimited'} minutes")
        logging.info(f"  Restart Interval: {self.RESTART_INTERVAL_HOURS} hours")
    
    async def run_live_stream_viewers(self, session_duration):
        """Run live stream viewers"""
        self.manager = MultiViewerManager()
        await self.manager.create_viewers(
            self.VIEWER_COUNT, 
            self.STREAM_URL, 
            session_duration
        )
    
    async def run_video_viewers(self):
        """Run regular video viewers"""
        if not self.VIDEO_URLS:
            logging.error("❌ No video URLs provided for VIDEO mode!")
            return
        
        # Create multiple viewers for videos
        tasks = []
        for i in range(1, self.VIEWER_COUNT + 1):
            viewer = YouTubeViewer()
            task = asyncio.create_task(
                self.run_single_video_viewer(viewer, i)
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def run_single_video_viewer(self, viewer, viewer_id):
        """Run a single video viewer through multiple videos"""
        try:
            await viewer.setup_browser()
            logging.info(f"👤 Viewer {viewer_id} started")
            
            session_start = asyncio.get_event_loop().time()
            session_duration_seconds = self.RESTART_INTERVAL_HOURS * 3600
            
            while (asyncio.get_event_loop().time() - session_start) < session_duration_seconds:
                # Pick a random video
                video_url = random.choice(self.VIDEO_URLS)
                
                logging.info(f"👤 Viewer {viewer_id} watching: {video_url}")
                success = await viewer.watch_video(video_url)
                
                if success:
                    logging.info(f"✅ Viewer {viewer_id} completed video")
                else:
                    logging.warning(f"⚠️ Viewer {viewer_id} failed to watch video")
                
                # Break between videos
                if self.is_running:
                    break_time = random.uniform(30, 120)  # 30s-2min break
                    await asyncio.sleep(break_time)
                else:
                    break
            
            logging.info(f"👤 Viewer {viewer_id} session completed")
            
        except Exception as e:
            logging.error(f"❌ Viewer {viewer_id} failed: {e}")
        finally:
            await viewer.close()
    
    async def run_viewers(self):
        """Run viewers with automatic restart capability"""
        while self.is_running:
            try:
                self.restart_count += 1
                logging.info(f"🚀 Starting viewer session #{self.restart_count} - Mode: {self.BOT_MODE}")
                
                # Set session duration (restart interval or max duration, whichever is shorter)
                session_duration = self.RESTART_INTERVAL_HOURS * 60  # Convert to minutes
                if self.MAX_DURATION_MINUTES:
                    session_duration = min(session_duration, self.MAX_DURATION_MINUTES)
                
                logging.info(f"Session will run for {session_duration} minutes")
                
                # Run based on mode
                if self.BOT_MODE == 'LIVE':
                    await self.run_live_stream_viewers(session_duration)
                elif self.BOT_MODE == 'VIDEO':
                    await self.run_video_viewers()
                elif self.BOT_MODE == 'MIXED':
                    # Randomly choose between live and video for each session
                    if random.choice([True, False]) and self.STREAM_URL != "https://www.youtube.com/watch?v=YOUR_STREAM_ID":
                        logging.info("🎥 Running LIVE stream session")
                        await self.run_live_stream_viewers(session_duration)
                    elif self.VIDEO_URLS:
                        logging.info("📹 Running VIDEO session")
                        await self.run_video_viewers()
                    else:
                        logging.error("❌ No valid URLs for MIXED mode!")
                        break
                
                logging.info(f"✅ Session #{self.restart_count} completed")
                
                if self.is_running:
                    logging.info(f"⏳ Waiting 60 seconds before restart...")
                    await asyncio.sleep(60)  # Brief pause between sessions
                
            except Exception as e:
                logging.error(f"❌ Session #{self.restart_count} failed: {e}")
                if self.is_running:
                    logging.info("⏳ Waiting 5 minutes before retry...")
                    await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def start(self):
        """Start the persistent bot"""
        self.is_running = True
        logging.info("🤖 YouTube Viewer Bot starting...")
        
        # Validate configuration
        if self.BOT_MODE == 'LIVE' and "YOUR_STREAM_ID" in self.STREAM_URL:
            logging.error("❌ Please update STREAM_URL with your actual stream URL for LIVE mode!")
            return
        elif self.BOT_MODE == 'VIDEO' and not self.VIDEO_URLS:
            logging.error("❌ Please provide VIDEO_URLS for VIDEO mode!")
            return
        elif self.BOT_MODE == 'MIXED' and "YOUR_STREAM_ID" in self.STREAM_URL and not self.VIDEO_URLS:
            logging.error("❌ Please provide either STREAM_URL or VIDEO_URLS for MIXED mode!")
            return
        
        try:
            await self.run_viewers()
        except KeyboardInterrupt:
            logging.info("⏹️ Bot stopped by user")
        except Exception as e:
            logging.error(f"❌ Bot crashed: {e}")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the bot gracefully"""
        self.is_running = False
        logging.info("🛑 Stopping bot...")
        
        if self.manager:
            await self.manager.stop_all_viewers()
        
        logging.info("✅ Bot stopped")

# Global bot instance for signal handling
bot = None

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    if bot:
        logging.info(f"📡 Received signal {signum}, shutting down...")
        asyncio.create_task(bot.stop())

async def main():
    """Main entry point"""
    global bot
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    bot = PersistentViewerBot()
    await bot.start()

if __name__ == "__main__":
    # Ensure event loop compatibility
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.run(main())