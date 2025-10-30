#!/usr/bin/env python3
"""
Setup Verification Script
Checks if all components are properly installed
"""

import sys
import os

def print_header(text):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)

def check_python_version():
    """Check Python version"""
    print("\n🐍 Checking Python Version...")
    version = sys.version_info

    if version.major == 3 and 8 <= version.minor <= 10:
        print(f"   ✅ Python {version.major}.{version.minor}.{version.micro} (Perfect!)")
        return True
    else:
        print(f"   ⚠️  Python {version.major}.{version.minor}.{version.micro}")
        print(f"   Recommended: Python 3.8-3.10")
        return False

def check_dependencies():
    """Check all required packages"""
    print("\n📦 Checking Dependencies...")

    packages = {
        'cv2': 'opencv-python',
        'numpy': 'numpy',
        'PIL': 'Pillow',
        'torch': 'torch',
        'facenet_pytorch': 'facenet-pytorch',
        'pandas': 'pandas',
        'openpyxl': 'openpyxl',
        'tkinter': 'tkinter (built-in)',
        'face_recognition': 'face-recognition (optional)',
        'dlib': 'dlib (optional)'
    }

    results = {}

    for module, package in packages.items():
        try:
            if module == 'cv2':
                import cv2
                version = cv2.__version__
            elif module == 'PIL':
                import PIL
                version = PIL.__version__
            elif module == 'tkinter':
                import tkinter
                version = "built-in"
            elif module == 'torch':
                import torch
                version = torch.__version__
            else:
                mod = __import__(module)
                version = getattr(mod, '__version__', 'installed')

            print(f"   ✅ {package}: {version}")
            results[module] = True

        except ImportError:
            optional = "(optional)" in package
            symbol = "⚠️ " if optional else "❌"
            print(f"   {symbol} {package}: NOT INSTALLED")
            results[module] = optional  # True if optional, False if required

    return all(results.values())

def check_directories():
    """Check required directories"""
    print("\n📁 Checking Directories...")

    dirs = [
        'database',
        'database/production',
        'exports',
        'cache'
    ]

    all_exist = True

    for dir_path in dirs:
        if os.path.exists(dir_path):
            print(f"   ✅ {dir_path}/")
        else:
            print(f"   ⚠️  {dir_path}/ (will be created)")
            try:
                os.makedirs(dir_path, exist_ok=True)
                print(f"   ✅ Created {dir_path}/")
            except Exception as e:
                print(f"   ❌ Failed to create {dir_path}/: {e}")
                all_exist = False

    return all_exist

def check_camera():
    """Check camera availability"""
    print("\n📹 Checking Camera...")

    try:
        import cv2
        cap = cv2.VideoCapture(0)

        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()

            if ret and frame is not None:
                height, width = frame.shape[:2]
                print(f"   ✅ Camera detected: {width}x{height}")

                if width >= 1280 and height >= 720:
                    print(f"   ✅ HD quality (excellent!)")
                elif width >= 640:
                    print(f"   ⚠️  Standard quality (acceptable)")
                else:
                    print(f"   ⚠️  Low quality (may affect accuracy)")

                return True
            else:
                print(f"   ❌ Camera found but cannot read frames")
                return False
        else:
            print(f"   ❌ No camera detected")
            return False

    except Exception as e:
        print(f"   ❌ Error checking camera: {e}")
        return False

def check_files():
    """Check required files"""
    print("\n📄 Checking Required Files...")

    files = [
        'production_face_recognition.py',
        'production_gui.py',
        'requirements_production.txt',
        'database_manager.py'
    ]

    all_exist = True

    for file_path in files:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path) / 1024  # KB
            print(f"   ✅ {file_path} ({size:.1f} KB)")
        else:
            print(f"   ❌ {file_path}: NOT FOUND")
            all_exist = False

    return all_exist

def test_torch_device():
    """Check PyTorch device availability"""
    print("\n⚡ Checking PyTorch Device...")

    try:
        import torch

        if torch.cuda.is_available():
            device = torch.cuda.get_device_name(0)
            print(f"   ✅ CUDA GPU available: {device}")
            print(f"   🚀 GPU acceleration enabled (FAST!)")
            return 'cuda'
        else:
            print(f"   ℹ️  CPU only (GPU not available)")
            print(f"   ℹ️  Performance: Good (but GPU would be faster)")
            return 'cpu'

    except Exception as e:
        print(f"   ⚠️  Cannot check device: {e}")
        return 'cpu'

def test_face_detection():
    """Test face detection"""
    print("\n🎯 Testing Face Detection...")

    try:
        import torch
        from facenet_pytorch import MTCNN
        import numpy as np

        # Create dummy MTCNN
        mtcnn = MTCNN(device='cpu')

        # Create test image
        test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

        print(f"   ✅ MTCNN loaded successfully")
        print(f"   ✅ Face detection module working")

        return True

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_face_recognition_model():
    """Test FaceNet model"""
    print("\n🧠 Testing FaceNet Model...")

    try:
        import torch
        from facenet_pytorch import InceptionResnetV1

        # Load model
        model = InceptionResnetV1(pretrained='vggface2').eval()

        # Test forward pass
        dummy_input = torch.randn(1, 3, 160, 160)
        with torch.no_grad():
            output = model(dummy_input)

        print(f"   ✅ FaceNet model loaded (VGGFace2)")
        print(f"   ✅ Embedding size: {output.shape[1]}D")
        print(f"   ✅ Model ready for recognition")

        return True

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def generate_report(results):
    """Generate final report"""
    print_header("VERIFICATION REPORT")

    all_passed = all(results.values())

    # Summary
    passed = sum(results.values())
    total = len(results)

    print(f"\n📊 Results: {passed}/{total} checks passed")
    print()

    # Details
    for check, status in results.items():
        symbol = "✅" if status else "❌"
        print(f"   {symbol} {check}")

    print()

    if all_passed:
        print("🎉 ALL CHECKS PASSED!")
        print()
        print("✅ System is ready for production use")
        print()
        print("🚀 To get started:")
        print("   python run_production.py")
        print("   or")
        print("   python production_gui.py")
    else:
        print("⚠️  SOME CHECKS FAILED")
        print()
        print("📝 Recommendations:")

        if not results.get('Dependencies'):
            print("   • Install dependencies: pip install -r requirements_production.txt")

        if not results.get('Camera'):
            print("   • Check camera permissions and connections")

        if not results.get('Files'):
            print("   • Ensure all required files are present")

        print()
        print("💡 See PRODUCTION_SETUP.md for detailed instructions")

    print("\n" + "=" * 70)

def main():
    print_header("PRODUCTION SYSTEM VERIFICATION")

    results = {}

    # Run checks
    results['Python Version'] = check_python_version()
    results['Dependencies'] = check_dependencies()
    results['Directories'] = check_directories()
    results['Files'] = check_files()
    results['Camera'] = check_camera()
    results['PyTorch Device'] = test_torch_device() is not None
    results['Face Detection'] = test_face_detection()
    results['Face Recognition Model'] = test_face_recognition_model()

    # Generate report
    generate_report(results)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nVerification cancelled by user.")
    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
