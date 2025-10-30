"""
Accuracy Testing and Benchmarking Script
Tests the production face recognition system
"""

import cv2
import numpy as np
from production_face_recognition import ProductionFaceRecognition
import time
from datetime import datetime
import os

class AccuracyTester:
    def __init__(self):
        self.system = ProductionFaceRecognition()
        self.system.load_database()

    def test_detection_speed(self, num_frames=100):
        """Test face detection speed"""
        print("\n🚀 Testing Face Detection Speed...")
        print("=" * 60)

        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        # Warm up
        for _ in range(10):
            cap.read()

        times = []
        detected_faces = []

        for i in range(num_frames):
            ret, frame = cap.read()
            if not ret:
                continue

            start = time.time()
            detections = self.system.detect_faces(frame)
            elapsed = time.time() - start

            times.append(elapsed)
            detected_faces.append(len(detections))

            if (i + 1) % 20 == 0:
                print(f"Progress: {i+1}/{num_frames} frames")

        cap.release()

        # Results
        avg_time = np.mean(times) * 1000  # Convert to ms
        fps = 1.0 / np.mean(times)
        avg_faces = np.mean(detected_faces)

        print(f"\n📊 Detection Performance:")
        print(f"   Average Detection Time: {avg_time:.2f} ms")
        print(f"   FPS: {fps:.1f}")
        print(f"   Average Faces per Frame: {avg_faces:.1f}")
        print(f"   Min/Max Time: {min(times)*1000:.2f}/{max(times)*1000:.2f} ms")

        return {
            'avg_time_ms': avg_time,
            'fps': fps,
            'avg_faces': avg_faces
        }

    def test_recognition_speed(self, num_tests=50):
        """Test recognition speed with registered faces"""
        print("\n🔍 Testing Recognition Speed...")
        print("=" * 60)

        if not self.system.encodings_db:
            print("❌ No registered students found. Please register students first.")
            return None

        print(f"Testing with {len(self.system.encodings_db)} registered students")

        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        times = []
        recognition_results = []

        print("Please position yourself in front of camera...")

        # Warm up
        for _ in range(10):
            cap.read()

        for i in range(num_tests):
            ret, frame = cap.read()
            if not ret:
                continue

            start = time.time()
            recognized = self.system.recognize_faces(frame, return_all=True)
            elapsed = time.time() - start

            times.append(elapsed)
            recognition_results.append(recognized)

            if (i + 1) % 10 == 0:
                print(f"Progress: {i+1}/{num_tests} frames")

        cap.release()

        # Analysis
        avg_time = np.mean(times) * 1000
        fps = 1.0 / np.mean(times)

        recognized_count = sum(1 for r in recognition_results for f in r if f['student_id'])
        unknown_count = sum(1 for r in recognition_results for f in r if not f['student_id'])

        print(f"\n📊 Recognition Performance:")
        print(f"   Average Recognition Time: {avg_time:.2f} ms")
        print(f"   FPS: {fps:.1f}")
        print(f"   Recognized Faces: {recognized_count}")
        print(f"   Unknown Faces: {unknown_count}")

        return {
            'avg_time_ms': avg_time,
            'fps': fps,
            'recognized': recognized_count,
            'unknown': unknown_count
        }

    def test_quality_assessment(self):
        """Test quality assessment under different conditions"""
        print("\n📸 Testing Quality Assessment...")
        print("=" * 60)
        print("Testing quality under different conditions:")
        print("1. Normal lighting")
        print("2. Move closer/farther")
        print("3. Turn face left/right")
        print("Press SPACE to capture test image, ESC to finish")

        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        test_results = []

        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            # Detect and assess
            detections = self.system.detect_faces(frame)

            display_frame = frame.copy()

            for detection in detections:
                x1, y1, x2, y2 = detection['bbox']
                quality = detection['quality']

                # Color based on quality
                if quality['overall'] >= 0.7:
                    color = (0, 255, 0)  # Green
                elif quality['overall'] >= 0.5:
                    color = (0, 165, 255)  # Orange
                else:
                    color = (0, 0, 255)  # Red

                cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 2)

                # Display metrics
                y_offset = y1 - 80
                cv2.putText(display_frame, f"Overall: {quality['overall']:.2f}",
                           (x1, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                cv2.putText(display_frame, f"Sharp: {quality['sharpness']:.2f}",
                           (x1, y_offset + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
                cv2.putText(display_frame, f"Bright: {quality['brightness']:.2f}",
                           (x1, y_offset + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
                cv2.putText(display_frame, f"Contrast: {quality['contrast']:.2f}",
                           (x1, y_offset + 60), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

            cv2.imshow('Quality Test', display_frame)

            key = cv2.waitKey(1) & 0xFF

            if key == ord(' ') and detections:
                # Record test result
                for detection in detections:
                    test_results.append(detection['quality'])
                    print(f"\n✅ Captured test {len(test_results)}:")
                    print(f"   Quality: {detection['quality']['overall']:.2f}")

            elif key == 27:  # ESC
                break

        cap.release()
        cv2.destroyAllWindows()

        if test_results:
            print(f"\n📊 Quality Test Summary ({len(test_results)} samples):")
            avg_quality = np.mean([q['overall'] for q in test_results])
            avg_sharpness = np.mean([q['sharpness'] for q in test_results])
            avg_brightness = np.mean([q['brightness'] for q in test_results])

            print(f"   Average Overall Quality: {avg_quality:.2f}")
            print(f"   Average Sharpness: {avg_sharpness:.2f}")
            print(f"   Average Brightness: {avg_brightness:.2f}")

        return test_results

    def test_registration_process(self):
        """Test the registration process"""
        print("\n📝 Testing Registration Process...")
        print("=" * 60)

        test_id = f"TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        test_name = "Test Student"

        print(f"Registering test student: {test_name}")
        print("This will test the multi-angle registration flow")

        result = self.system.register_student(
            student_id=test_id,
            name=test_name,
            email="test@example.com",
            department="Testing",
            year=1
        )

        if result['success']:
            print(f"\n✅ Registration Test Passed!")
            print(f"   Student ID: {test_id}")
            print(f"   Images Captured: {result['num_images']}")

            # Test recognition immediately
            print("\n🔍 Testing immediate recognition...")
            print("Please stay in front of camera...")

            cap = cv2.VideoCapture(0)
            recognized = False
            attempts = 0
            max_attempts = 50

            while attempts < max_attempts and not recognized:
                ret, frame = cap.read()
                if not ret:
                    continue

                results = self.system.recognize_faces(frame, return_all=True)

                for face in results:
                    if face['student_id'] == test_id:
                        print(f"\n✅ Recognition Test Passed!")
                        print(f"   Recognized as: {face['name']}")
                        print(f"   Confidence: {face['confidence']:.3f}")
                        recognized = True
                        break

                attempts += 1

            cap.release()

            if not recognized:
                print(f"\n⚠️ Recognition test inconclusive ({max_attempts} attempts)")

            # Cleanup test student
            if test_id in self.system.encodings_db:
                del self.system.encodings_db[test_id]
                del self.system.student_metadata[test_id]
                print(f"\n🧹 Cleaned up test student")
        else:
            print(f"\n❌ Registration Test Failed!")
            print(f"   Error: {result.get('error')}")

        return result

    def run_full_benchmark(self):
        """Run complete benchmark suite"""
        print("\n" + "=" * 60)
        print("🎯 PRODUCTION FACE RECOGNITION BENCHMARK")
        print("=" * 60)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Registered Students: {len(self.system.encodings_db)}")
        print("=" * 60)

        results = {}

        # Test 1: Detection Speed
        results['detection'] = self.test_detection_speed(num_frames=100)

        # Test 2: Recognition Speed (if students registered)
        if self.system.encodings_db:
            results['recognition'] = self.test_recognition_speed(num_tests=50)

        # Test 3: Quality Assessment
        print("\n📸 Quality assessment test (optional)")
        choice = input("Run quality assessment test? (y/n): ")
        if choice.lower() == 'y':
            results['quality'] = self.test_quality_assessment()

        # Test 4: Registration Process
        print("\n📝 Registration process test (optional)")
        choice = input("Run registration test? (y/n): ")
        if choice.lower() == 'y':
            results['registration'] = self.test_registration_process()

        # Summary
        print("\n" + "=" * 60)
        print("📊 BENCHMARK SUMMARY")
        print("=" * 60)

        if 'detection' in results:
            print(f"✅ Detection: {results['detection']['fps']:.1f} FPS ({results['detection']['avg_time_ms']:.2f} ms)")

        if 'recognition' in results:
            print(f"✅ Recognition: {results['recognition']['fps']:.1f} FPS ({results['recognition']['avg_time_ms']:.2f} ms)")

        print("\n💡 Recommendations:")
        if 'detection' in results:
            fps = results['detection']['fps']
            if fps >= 20:
                print("   ✅ Excellent performance! Real-time capable.")
            elif fps >= 15:
                print("   ✅ Good performance. Suitable for most use cases.")
            elif fps >= 10:
                print("   ⚠️ Moderate performance. Consider optimization.")
            else:
                print("   ❌ Low performance. Check system requirements.")

        print("\n" + "=" * 60)
        print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        return results


def main():
    print("\n🎯 Face Recognition System - Accuracy Tester")
    print("=" * 60)

    tester = AccuracyTester()

    while True:
        print("\n📋 Available Tests:")
        print("1. Detection Speed Test")
        print("2. Recognition Speed Test")
        print("3. Quality Assessment Test")
        print("4. Registration Process Test")
        print("5. Full Benchmark Suite")
        print("6. Exit")

        choice = input("\nSelect test (1-6): ").strip()

        if choice == '1':
            tester.test_detection_speed()
        elif choice == '2':
            tester.test_recognition_speed()
        elif choice == '3':
            tester.test_quality_assessment()
        elif choice == '4':
            tester.test_registration_process()
        elif choice == '5':
            tester.run_full_benchmark()
        elif choice == '6':
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()
