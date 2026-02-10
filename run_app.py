import subprocess
import time
import sys
import os
import signal

def run_app():
    print("🚀 Starting Outlook FAQ Extractor App...")
    
    # 1. Start the Background FAQ Extractor
    print("🤖 Starting Background FAQ Extractor...")
    extractor_process = subprocess.Popen([sys.executable, "faq_extractor.py"])
    
    # 2. Start the Streamlit UI
    print("🎨 Starting Streamlit User Interface...")
    # We use 'streamlit run main.py'
    # We need to find where 'streamlit' executable is, or use sys.executable -m streamlit
    ui_process = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "main.py"])
    
    print("\n✅ Application works are running!")
    print("   - Backend PID:Provider")
    print(f"   - Frontend PID: {ui_process.pid}")
    print("\n👉 Press Ctrl+C to stop both services.\n")
    
    try:
        # Keep the script running to monitor processes
        while True:
            time.sleep(1)
            
            # Check if processes are still alive
            if extractor_process.poll() is not None:
                print("❌ Background Extractor stopped unexpectedly.")
                break
            if ui_process.poll() is not None:
                print("❌ UI stopped unexpectedly.")
                break
                
    except KeyboardInterrupt:
        print("\n🛑 Stopping services...")
    finally:
        # Terminate processes
        extractor_process.terminate()
        ui_process.terminate()
        
        # Wait for them to exit
        extractor_process.wait()
        ui_process.wait()
        print("👋 Goodbye!")

if __name__ == "__main__":
    run_app()
