#!/usr/bin/env python3
# app/test_runner.py - Test runner for all forex bot tests

import sys
import os
import importlib.util
from pathlib import Path

def run_test_file(test_file_path, test_name):
    """Ejecuta un archivo de test específico"""
    print(f"\n{'='*60}")
    print(f"🧪 Running {test_name}")
    print(f"{'='*60}")
    
    try:
        # Cargar el módulo dinámicamente
        spec = importlib.util.spec_from_file_location(test_name, test_file_path)
        module = importlib.util.module_from_spec(spec)
        
        # Agregar el directorio raíz al path para imports
        root_dir = Path(__file__).parent.parent
        if str(root_dir) not in sys.path:
            sys.path.insert(0, str(root_dir))
        
        # Ejecutar el módulo
        spec.loader.exec_module(module)
        
        # Si tiene función main, ejecutarla
        if hasattr(module, 'main'):
            result = module.main()
            return result if result is not None else True
        
        # Si tiene función run_all_tests, ejecutarla
        elif hasattr(module, 'run_all_tests'):
            result = module.run_all_tests()
            return result if result is not None else True
        
        # Si no tiene función específica, asumimos que se ejecutó correctamente
        else:
            print(f"✅ {test_name} executed successfully")
            return True
            
    except Exception as e:
        print(f"❌ Error running {test_name}: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Función principal que ejecuta todos los tests"""
    print("🚀 FOREX BOT - COMPREHENSIVE TEST SUITE")
    print("=" * 60)
    
    # Directorio de tests
    test_dir = Path(__file__).parent.parent / "test"
    
    if not test_dir.exists():
        print(f"❌ Test directory not found: {test_dir}")
        return False
    
    # Lista de archivos de test a ejecutar
    test_files = [
        ("simple_test.py", "Simple Test"),
        ("test_candle_strategies.py", "Candle Strategies Test"),
        ("verify_candle_strategies.py", "Candle Strategies Verification")
    ]
    
    results = {}
    total_tests = 0
    passed_tests = 0
    
    # Ejecutar cada test
    for test_file, test_name in test_files:
        test_path = test_dir / test_file
        
        if test_path.exists():
            total_tests += 1
            success = run_test_file(test_path, test_name)
            results[test_name] = success
            if success:
                passed_tests += 1
        else:
            print(f"⚠️  Test file not found: {test_path}")
    
    # Resumen final
    print(f"\n{'='*60}")
    print("🏁 FINAL TEST SUMMARY")
    print(f"{'='*60}")
    
    for test_name, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status} - {test_name}")
    
    print(f"\nTotal Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "0%")
    
    if passed_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED! Forex bot is ready for deployment.")
    else:
        print(f"\n⚠️  {total_tests - passed_tests} test(s) failed. Check output above for details.")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
