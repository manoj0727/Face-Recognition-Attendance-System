#!/usr/bin/env python3
"""
Production Face Recognition Attendance System Launcher
Quick start script for the production system
"""

import sys
import os

def check_dependencies():
    """Check if all required packages are installed"""
    required = [
        'cv2',
        'numpy',
        'PIL',
        'torch',
        'facenet_pytorch',
        'tkinter',
        'pandas'
    ]

    missing = []

    for package in required:
        try:
            if package == 'cv2':
                import cv2
            elif package == 'PIL':
                import PIL
            elif package == 'tkinter':
                import tkinter
            else:
                __import__(package)
        except ImportError:
            missing.append(package)

    return missing

def main():
    print("=" * 70)
    print("🚀 PRODUCTION FACE RECOGNITION ATTENDANCE SYSTEM")
    print("=" * 70)
    print()

    # Check Python version
    if sys.version_info < (3, 8) or sys.version_info >= (3, 11):
        print("⚠️  WARNING: Python 3.8-3.10 recommended")
        print(f"   Current version: {sys.version_info.major}.{sys.version_info.minor}")
        print()

    # Check dependencies
    print("🔍 Checking dependencies...")
    missing = check_dependencies()

    if missing:
        print("❌ Missing dependencies:")
        for pkg in missing:
            print(f"   - {pkg}")
        print()
        print("📦 Install with:")
        print("   pip install -r requirements_production.txt")
        print()
        return

    print("✅ All dependencies installed")
    print()

    # Create directories
    print("📁 Creating required directories...")
    os.makedirs('database/production', exist_ok=True)
    os.makedirs('exports', exist_ok=True)
    os.makedirs('cache', exist_ok=True)
    print("✅ Directories ready")
    print()

    # Launch options
    print("=" * 70)
    print("Choose launch mode:")
    print()
    print("1. 🖥️  Production GUI (Recommended)")
    print("2. 🧪 Run Accuracy Tests")
    print("3. 📚 View Setup Guide")
    print("4. ❌ Exit")
    print()

    choice = input("Enter choice (1-4): ").strip()

    if choice == '1':
        print()
        print("🚀 Launching Production GUI...")
        print("=" * 70)
        from production_gui import main as gui_main
        gui_main()

    elif choice == '2':
        print()
        print("🧪 Launching Accuracy Tests...")
        print("=" * 70)
        from test_accuracy import main as test_main
        test_main()

    elif choice == '3':
        print()
        print("📚 Opening Setup Guide...")
        print("=" * 70)
        if os.path.exists('PRODUCTION_SETUP.md'):
            with open('PRODUCTION_SETUP.md', 'r') as f:
                print(f.read())
        else:
            print("❌ Setup guide not found!")

    elif choice == '4':
        print("Goodbye!")

    else:
        print("❌ Invalid choice!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Try running: python production_gui.py")
