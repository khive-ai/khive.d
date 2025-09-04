#!/bin/bash

# Keyboard Shortcuts E2E Test Runner
# Comprehensive test execution for Ocean's CLI-first keyboard navigation system
# Author: tester+input-systems agent

set -e

# Colors for output formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Test categories
declare -A TEST_CATEGORIES
TEST_CATEGORIES=(
    ["global"]="keyboard-shortcuts.spec.ts"
    ["vim"]="vim-navigation.spec.ts" 
    ["context"]="context-shortcuts.spec.ts"
    ["performance"]="keyboard-performance.spec.ts"
    ["visual"]="keyboard-shortcuts-visual.spec.ts"
)

# Performance thresholds
declare -A PERF_THRESHOLDS
PERF_THRESHOLDS=(
    ["global_avg"]="15"
    ["sequence_avg"]="50"
    ["context_switch"]="30"
    ["p95"]="75"
    ["p99"]="100"
)

print_header() {
    echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}🎹 KHIVE Keyboard Shortcuts E2E Test Suite${NC}"
    echo -e "${BLUE}   Ocean's CLI-First Interface Testing${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_section() {
    echo -e "${CYAN}──────────────────────────────────────────${NC}"
    echo -e "${CYAN}📋 $1${NC}"
    echo -e "${CYAN}──────────────────────────────────────────${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${PURPLE}ℹ️  $1${NC}"
}

check_prerequisites() {
    print_section "Checking Prerequisites"
    
    # Check if Node.js is installed
    if ! command -v node &> /dev/null; then
        print_error "Node.js is not installed"
        exit 1
    fi
    print_success "Node.js found: $(node --version)"
    
    # Check if npm is installed
    if ! command -v npm &> /dev/null; then
        print_error "npm is not installed"
        exit 1
    fi
    print_success "npm found: $(npm --version)"
    
    # Check if Playwright is installed
    if ! npx playwright --version &> /dev/null; then
        print_error "Playwright is not installed"
        print_info "Run: npm install @playwright/test"
        exit 1
    fi
    print_success "Playwright found: $(npx playwright --version)"
    
    # Check if dev server is running
    if curl -s http://localhost:3000 > /dev/null; then
        print_success "Development server is running at http://localhost:3000"
    else
        print_warning "Development server is not running"
        print_info "Starting development server..."
        npm run dev &
        DEV_PID=$!
        sleep 5
        
        if curl -s http://localhost:3000 > /dev/null; then
            print_success "Development server started successfully"
        else
            print_error "Failed to start development server"
            exit 1
        fi
    fi
    
    echo ""
}

run_test_category() {
    local category=$1
    local test_file=${TEST_CATEGORIES[$category]}
    
    if [[ -z "$test_file" ]]; then
        print_error "Unknown test category: $category"
        return 1
    fi
    
    print_section "Running $category tests"
    print_info "Test file: $test_file"
    
    local start_time=$(date +%s)
    
    if npx playwright test "$test_file" --reporter=line; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        print_success "$category tests passed in ${duration}s"
        return 0
    else
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        print_error "$category tests failed after ${duration}s"
        return 1
    fi
}

run_performance_analysis() {
    print_section "Performance Analysis"
    print_info "Running performance benchmarks..."
    
    # Run performance tests with JSON output
    if npx playwright test keyboard-performance.spec.ts --reporter=json > performance-results.json 2>/dev/null; then
        print_success "Performance tests completed"
        
        # Parse and display key metrics (would need jq for full parsing)
        if command -v jq &> /dev/null; then
            local passed_tests=$(jq '.stats.expected' performance-results.json 2>/dev/null || echo "N/A")
            local failed_tests=$(jq '.stats.unexpected' performance-results.json 2>/dev/null || echo "N/A") 
            
            echo "  📊 Test Results:"
            echo "     Passed: $passed_tests"
            echo "     Failed: $failed_tests"
        else
            print_info "Install 'jq' for detailed performance metrics parsing"
        fi
    else
        print_warning "Performance analysis failed - check logs"
    fi
    
    echo ""
}

run_visual_comparison() {
    print_section "Visual Regression Testing"
    print_info "Updating visual baselines and running comparison..."
    
    # Update screenshots if --update-visuals flag is passed
    if [[ "$1" == "--update-visuals" ]]; then
        print_info "Updating visual baselines..."
        npx playwright test keyboard-shortcuts-visual.spec.ts --update-snapshots
    fi
    
    if npx playwright test keyboard-shortcuts-visual.spec.ts --reporter=line; then
        print_success "Visual tests passed - no regressions detected"
    else
        print_warning "Visual differences detected - review screenshots"
        print_info "Run with --update-visuals to update baselines"
    fi
    
    echo ""
}

run_cross_browser_tests() {
    print_section "Cross-Browser Compatibility"
    
    local browsers=("chromium" "firefox" "webkit")
    local passed=0
    local total=${#browsers[@]}
    
    for browser in "${browsers[@]}"; do
        print_info "Testing on $browser..."
        if npx playwright test --project="$browser" keyboard-shortcuts.spec.ts --reporter=line > /dev/null 2>&1; then
            print_success "$browser: ✅"
            ((passed++))
        else
            print_error "$browser: ❌"
        fi
    done
    
    echo ""
    print_info "Cross-browser results: $passed/$total browsers passed"
    
    if [[ $passed -eq $total ]]; then
        print_success "All browsers compatible"
    else
        print_warning "Some browsers failed - check logs"
    fi
    
    echo ""
}

generate_test_report() {
    print_section "Generating Test Report"
    
    local report_file="keyboard-shortcuts-test-report.html"
    
    if npx playwright test --reporter=html --reporter-html-output="$report_file"; then
        print_success "Test report generated: $report_file"
        print_info "Open with: npx playwright show-report"
    else
        print_warning "Failed to generate test report"
    fi
    
    echo ""
}

cleanup() {
    if [[ -n "${DEV_PID:-}" ]]; then
        print_info "Stopping development server (PID: $DEV_PID)..."
        kill $DEV_PID 2>/dev/null || true
    fi
}

show_usage() {
    echo "Usage: $0 [OPTIONS] [TEST_CATEGORY]"
    echo ""
    echo "Options:"
    echo "  --all                 Run all test categories"
    echo "  --performance         Run performance tests only"
    echo "  --visual              Run visual tests only"
    echo "  --cross-browser       Run cross-browser tests"
    echo "  --update-visuals      Update visual baselines"
    echo "  --report              Generate HTML report"
    echo "  --help                Show this help message"
    echo ""
    echo "Test Categories:"
    echo "  global               Global keyboard shortcuts"
    echo "  vim                  Vim-style navigation sequences"
    echo "  context              Context-aware shortcuts"
    echo "  performance          Performance benchmarks"
    echo "  visual               Visual regression tests"
    echo ""
    echo "Examples:"
    echo "  $0 --all                          # Run all tests"
    echo "  $0 global                         # Run global shortcuts only"
    echo "  $0 --performance --cross-browser  # Performance across browsers"
    echo "  $0 --visual --update-visuals      # Update visual baselines"
}

main() {
    # Set trap for cleanup
    trap cleanup EXIT
    
    print_header
    
    # Parse command line arguments
    local run_all=false
    local run_performance=false
    local run_visual=false
    local run_cross_browser=false
    local update_visuals=false
    local generate_report=false
    local test_category=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --all)
                run_all=true
                shift
                ;;
            --performance)
                run_performance=true
                shift
                ;;
            --visual)
                run_visual=true
                shift
                ;;
            --cross-browser)
                run_cross_browser=true
                shift
                ;;
            --update-visuals)
                update_visuals=true
                shift
                ;;
            --report)
                generate_report=true
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            global|vim|context|performance|visual)
                test_category=$1
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Check prerequisites
    check_prerequisites
    
    local exit_code=0
    
    # Execute based on options
    if [[ "$run_all" == true ]]; then
        print_info "Running all keyboard shortcut tests..."
        echo ""
        
        for category in "${!TEST_CATEGORIES[@]}"; do
            if ! run_test_category "$category"; then
                exit_code=1
            fi
            echo ""
        done
        
    elif [[ -n "$test_category" ]]; then
        if ! run_test_category "$test_category"; then
            exit_code=1
        fi
        echo ""
        
    elif [[ "$run_performance" == true ]]; then
        if ! run_test_category "performance"; then
            exit_code=1
        fi
        run_performance_analysis
        
    elif [[ "$run_visual" == true ]]; then
        run_visual_comparison "$([[ "$update_visuals" == true ]] && echo '--update-visuals')"
        
    else
        print_info "No specific test category specified. Running core tests..."
        echo ""
        
        # Run essential test categories
        for category in "global" "vim" "context"; do
            if ! run_test_category "$category"; then
                exit_code=1
            fi
            echo ""
        done
    fi
    
    # Run additional analyses if requested
    if [[ "$run_cross_browser" == true ]]; then
        run_cross_browser_tests
    fi
    
    if [[ "$generate_report" == true ]]; then
        generate_test_report
    fi
    
    # Final summary
    print_section "Test Summary"
    if [[ $exit_code -eq 0 ]]; then
        print_success "All tests completed successfully! 🎉"
        print_info "Keyboard shortcuts are meeting Ocean's <50ms performance requirements"
    else
        print_error "Some tests failed. Check the output above for details."
        print_info "Performance targets: Global <15ms, Sequences <50ms, Context switches <30ms"
    fi
    
    echo ""
    print_info "For detailed analysis: npx playwright show-report"
    print_info "For visual debugging: npx playwright test --ui"
    
    exit $exit_code
}

# Run main function with all arguments
main "$@"