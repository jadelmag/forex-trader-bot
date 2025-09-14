# app/__main__.py - Entry point for python -m app

import sys
from pathlib import Path

def main():
    # Agregar directorio raíz al path
    root_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(root_dir))
    
    # Verificar argumentos
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'test':
            from app.test_runner import main as run_tests
            success = run_tests()
            sys.exit(0 if success else 1)
            
        elif command == 'run' or command == 'start':
            from app.main import main as run_app
            run_app()
            sys.exit(0)
            
        elif command == 'help':
            print("🤖 Forex Bot - Available Commands:")
            print("=" * 50)
            print("  python -m app run     # Launch the main application")
            print("  python -m app start   # Launch the main application (alias)")
            print("  python -m app test    # Run all tests")
            print("  python -m app help    # Show this help message")
            print()
            print("📁 Test Files Available:")
            print("  check_detection_with_draw_candles  # Check detection with draw candles")
            print("  test_risk_manager_orders  # RiskManager Orders Test")
            print()
            print("💡 Usage Examples:")
            print("  python -m app run     # Launch the forex trading application")
            print("  python -m app test    # Execute comprehensive test suite")
            sys.exit(0)
            
        else:
            print(f"❌ Unknown command: {command}")
            print("Use 'python -m app help' to see available commands")
            sys.exit(1)
    else:
        print("Forex Bot - Available commands:")
        print("  python -m app run     # Launch the main application")
        print("  python -m app test    # Run all tests")
        print("  python -m app help    # Show help")
        print()
        print("Use 'python -m app help' for more details")
        sys.exit(1)

if __name__ == "__main__":
    main()
