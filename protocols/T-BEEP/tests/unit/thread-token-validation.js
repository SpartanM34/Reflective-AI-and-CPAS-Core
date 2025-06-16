// T-BEEP Protocol Unit Tests - Thread Token Validation
// Mobile-friendly: Copy-paste ready test functions

const TBEEPValidator = require('../../core/validators.js');

// Test cases for thread token validation
const threadTokenTests = {
  
  validTokens: [
    '#COMM_PROTO006.0',
    '#SOFTWARE_PROJ_001.1',
    '#CODE_REVIEW_042.2',
    '#RESEARCH_SYNTH_123.15'
  ],
  
  invalidTokens: [
    'COMM_PROTO006.0',           // Missing #
    '#comm_proto006.0',          // Lowercase
    '#COMM-PROTO-006.0',         // Hyphens instead of underscores
    '#COMM_PROTO.0',             // Missing numbers
    '#COMM_PROTO006',            // Missing version
    '#COMM_PROTO006.0.1',        // Too many version parts
    ''                           // Empty string
  ],
  
  // Run all validation tests
  runTests: function() {
    console.log('🧪 Running Thread Token Validation Tests...\n');
    
    let passed = 0;
    let failed = 0;
    
    // Test valid tokens
    console.log('✅ Testing Valid Tokens:');
    this.validTokens.forEach(token => {
      const result = TBEEPValidator.validateThreadToken(token);
      if (result) {
        console.log(`   ✓ ${token} - PASS`);
        passed++;
      } else {
        console.log(`   ✗ ${token} - FAIL (should be valid)`);
        failed++;
      }
    });
    
    // Test invalid tokens  
    console.log('\n❌ Testing Invalid Tokens:');
    this.invalidTokens.forEach(token => {
      const result = TBEEPValidator.validateThreadToken(token);
      if (!result) {
        console.log(`   ✓ "${token}" - PASS (correctly rejected)`);
        passed++;
      } else {
        console.log(`   ✗ "${token}" - FAIL (should be invalid)`);
        failed++;
      }
    });
    
    // Summary
    console.log(`\n📊 Test Results:`);
    console.log(`   Passed: ${passed}`);
    console.log(`   Failed: ${failed}`);
    console.log(`   Total: ${passed + failed}`);
    
    if (failed === 0) {
      console.log('🎉 All tests passed!');
    } else {
      console.log('⚠️ Some tests failed - check implementation');
    }
    
    return { passed, failed, total: passed + failed };
  }
};

// Human-friendly test runner
function runMobileTests() {
  console.log('📱 Mobile-Friendly T-BEEP Test Suite');
  console.log('=====================================\n');
  
  const results = threadTokenTests.runTests();
  
  console.log('\n📋 Next Steps:');
  if (results.failed > 0) {
    console.log('1. Fix failing validation logic');
    console.log('2. Re-run tests');
    console.log('3. Update implementation if needed');
  } else {
    console.log('1. ✅ Thread token validation working correctly');
    console.log('2. Ready to test other T-BEEP components');
    console.log('3. Consider adding more edge cases');
  }
}

// Export for use in other test files
if (typeof module !== 'undefined') {
  module.exports = { threadTokenTests, runMobileTests };
}

// Auto-run if called directly (mobile-friendly)
if (typeof window === 'undefined' && require.main === module) {
  runMobileTests();
}
