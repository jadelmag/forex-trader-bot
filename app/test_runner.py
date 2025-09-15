#!/usr/bin/env python3
# app/test_runner.py - Test runner for all forex bot tests

import sys
import os
import importlib.util
import argparse
from pathlib import Path

def run_test_file(test_file_path, test_name):
    """Ejecuta un archivo de test específico"""
    print(f"\n{'='*60}")
    print(f"🧪 Running {test_name}")
    print(f"📁 Path: {test_file_path}")
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
            print(f"🚀 Executing main() function...")
            result = module.main()
            print(f"✅ {test_name} completed successfully")
            return result if result is not None else True
        
        # Si tiene función run_all_tests, ejecutarla
        elif hasattr(module, 'run_all_tests'):
            print(f"🚀 Executing run_all_tests() function...")
            result = module.run_all_tests()
            print(f"✅ {test_name} completed successfully")
            return result if result is not None else True
        
        # Si no tiene función específica, asumimos que se ejecutó correctamente
        else:
            print(f"✅ {test_name} executed successfully (no main function found)")
            return True
            
    except KeyboardInterrupt:
        print(f"⚠️ {test_name} interrupted by user")
        return False
    except Exception as e:
        print(f"❌ Error running {test_name}: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_specific_test(test_name_filter):
    """Ejecuta un test específico basado en el filtro"""
    print(f"🎯 FOREX BOT - RUNNING SPECIFIC TEST: {test_name_filter}")
    print("=" * 60)
    
    test_dir = Path(__file__).parent.parent / "test"
    
    if not test_dir.exists():
        print(f"❌ Test directory not found: {test_dir}")
        return False
    
    # Lista completa de tests
    all_test_files = [
        ("test_risk_manager_orders.py", "RiskManager Orders Test"),
        ("check_detection_with_draw_candles.py", "Comprehensive Trading Simulation Test")
    ]
    
    # Filtrar tests que coincidan
    matching_tests = []
    for test_file, test_name in all_test_files:
        if test_name_filter.lower() in test_name.lower() or test_name_filter.lower() in test_file.lower():
            matching_tests.append((test_file, test_name))
    
    if not matching_tests:
        print(f"❌ No tests found matching '{test_name_filter}'")
        print("\nAvailable tests:")
        for test_file, test_name in all_test_files:
            print(f"  - {test_name} ({test_file})")
        return False
    
    print(f"Found {len(matching_tests)} matching test(s):")
    for test_file, test_name in matching_tests:
        print(f"  - {test_name}")
    
    # Ejecutar tests coincidentes
    results = {}
    total_tests = 0
    passed_tests = 0
    
    for test_file, test_name in matching_tests:
        test_path = test_dir / test_file
        
        if test_path.exists():
            total_tests += 1
            success = run_test_file(test_path, test_name)
            results[test_name] = success
            if success:
                passed_tests += 1
        else:
            print(f"⚠️  Test file not found: {test_path}")
    
    # Mostrar resultados
    print(f"\n{'='*60}")
    print("🏁 SPECIFIC TEST RESULTS")
    print(f"{'='*60}")
    
    for test_name, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status} - {test_name}")
    
    print(f"\nTests Run: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    
    return passed_tests == total_tests

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
        ("test_risk_manager_orders.py", "RiskManager Orders Test"),
        ("check_detection_with_draw_candles.py", "Comprehensive Trading Simulation Test")
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
    parser = argparse.ArgumentParser(description='Forex Bot Test Runner')
    parser.add_argument('--test', '-t', type=str, help='Run specific test(s) matching the given name/pattern')
    parser.add_argument('--list', '-l', action='store_true', help='List all available tests')
    parser.add_argument('--simulation', '-s', action='store_true', help='Run only the comprehensive trading simulation test')
    
    args = parser.parse_args()
    
    if args.list:
        print("📋 AVAILABLE TESTS:")
        print("=" * 60)
        test_files = [
            ("test_risk_manager_orders.py", "RiskManager Orders Test"),
            ("check_detection_with_draw_candles.py", "Comprehensive Trading Simulation Test")
        ]
        for i, (test_file, test_name) in enumerate(test_files, 1):
            print(f"{i:2d}. {test_name}")
            print(f"    📁 {test_file}")
        print(f"\nUsage examples:")
        print(f"  python test_runner.py --test simulation")
        print(f"  python test_runner.py --test candle")
        print(f"  python test_runner.py --simulation")
        sys.exit(0)
    
    elif args.simulation:
        success = run_specific_test("Comprehensive Trading Simulation")
        sys.exit(0 if success else 1)
    
    elif args.test:
        success = run_specific_test(args.test)
        sys.exit(0 if success else 1)
    
    else:
        success = main()
        sys.exit(0 if success else 1)
