// T-BEEP Protocol Runtime Validation
// Mobile-friendly: Copy-paste ready validation functions

const TBEEPValidator = {
  validateThreadToken: function(token) {
    const pattern = /^#[A-Z_]+\d{3,4}\.\d+$/;
    return pattern.test(token);
  },
  
  validateMetadataInheritance: function(message) {
    const required = ['thread_token', 'instance', 'reasoning_level', 'confidence'];
    return required.every(field => message.hasOwnProperty(field));
  },
  
  validateSchemaCompliance: function(instance_spec) {
    // Progressive validation - non-breaking
    const warnings = [];
    const errors = [];
    
    if (!instance_spec.declared_capabilities) {
      warnings.push('Missing declared_capabilities - recommended for full compliance');
    }
    
    if (!instance_spec.instance_name) {
      errors.push('instance_name is required');
    }
    
    return { valid: errors.length === 0, warnings, errors };
  },
  
  // Human-safe validation with clear feedback
  humanFriendlyValidation: function(data) {
    const result = this.validateSchemaCompliance(data);
    if (!result.valid) {
      console.log('❌ Validation failed:', result.errors);
    } else if (result.warnings.length > 0) {
      console.log('⚠️ Validation passed with warnings:', result.warnings);
    } else {
      console.log('✅ Full validation passed');
    }
    return result;
  }
};

// Export for use in other files
if (typeof module !== 'undefined') {
  module.exports = TBEEPValidator;
}
