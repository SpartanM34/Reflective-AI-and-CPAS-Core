// T-BEEP Reference Implementation - JavaScript Messenger
// Mobile-friendly: Copy-paste ready collaboration tool

class TBEEPMessenger {
  constructor(instanceName, baseConfig = {}) {
    this.instanceName = instanceName;
    this.currentThread = null;
    this.messageHistory = [];
    this.config = {
      reasoningLevel: 'Detailed',
      confidenceDefault: 'Medium',
      collaborationMode: 'Discussion',
      ...baseConfig
    };
  }
  
  // Create a new T-BEEP formatted message
  createMessage(options = {}, seedToken) {
    const timestamp = new Date().toISOString();
    const threadToken = options.threadToken || this.generateThreadToken();
    
    const message = {
      threadToken: threadToken,
      instance: this.instanceName,
      reasoningLevel: options.reasoningLevel || this.config.reasoningLevel,
      confidence: options.confidence || this.config.confidenceDefault,
      collaborationMode: options.collaborationMode || this.config.collaborationMode,
      timestamp: timestamp,
      version: options.version || this.generateVersion(threadToken),
      resources: options.resources || [],
      handoff: options.handoff || [],
      content: options.content || ''
    };

    if (seedToken) {
      message.seedToken = seedToken;
    }
    
    this.messageHistory.push(message);
    this.currentThread = threadToken;
    
    return message;
  }
  
  // Format message for mobile copy-paste
  formatForMobile(message) {
    return `🔹 Thread Token: ${message.threadToken}
🔹 Instance: ${message.instance}
🧠 Reasoning Level: ${message.reasoningLevel}
📊 Confidence: ${message.confidence}
🤝 Collaboration Mode: ${message.collaborationMode}
⏰ Timestamp: ${message.timestamp}
🔢 Version: ${message.version}
📎 Resources: [${message.resources.join(', ')}]
🔁 Handoff: ${message.handoff.join(', ')}

${message.content}`;
  }
  
  // Generate thread token
  generateThreadToken(projectName = 'COLLAB') {
    const num = Math.floor(Math.random() * 1000).toString().padStart(3, '0');
    return `#${projectName}_${num}.0`;
  }
  
  // Generate version string
  generateVersion(threadToken) {
    const base = threadToken.split('.')[0].replace('#', '');
    const versionNum = this.messageHistory.filter(m => 
      m.threadToken.startsWith(threadToken.split('.')[0])
    ).length;
    return `#${base}.v${versionNum + 1}.0`;
  }
  
  // Continue existing thread
  continueThread(threadToken, options = {}) {
    const versionParts = threadToken.split('.');
    const newVersion = `${versionParts[0]}.${parseInt(versionParts[1]) + 1}`;
    
    return this.createMessage({
      ...options,
      threadToken: newVersion
    });
  }
  
  // Validate message format
  validateMessage(message) {
    const required = ['threadToken', 'instance', 'reasoningLevel', 'confidence'];
    const missing = required.filter(field => !message[field]);
    
    return {
      valid: missing.length === 0,
      missing: missing,
      warnings: this.getValidationWarnings(message)
    };
  }
  
  getValidationWarnings(message) {
    const warnings = [];
    
    if (!message.handoff || message.handoff.length === 0) {
      warnings.push('No handoff specified - conversation may stall');
    }
    
    if (!message.resources || message.resources.length === 0) {
      warnings.push('No resources listed - context may be unclear');
    }
    
    if (message.content.length < 10) {
      warnings.push('Very short content - may need more detail');
    }
    
    return warnings;
  }
  
  // Human-friendly helper methods
  quickMessage(content, handoffTo = [], seedToken) {
    const message = this.createMessage({
      content: content,
      handoff: handoffTo,
      collaborationMode: 'Quick Discussion'
    }, seedToken);
    
    return this.formatForMobile(message);
  }
  
  technicalMessage(content, resources = [], handoffTo = [], seedToken) {
    const message = this.createMessage({
      content: content,
      resources: resources,
      handoff: handoffTo,
      reasoningLevel: 'Deep Technical Analysis',
      collaborationMode: 'Technical Review'
    }, seedToken);
    
    return this.formatForMobile(message);
  }
}

// Mobile-friendly usage examples
const exampleUsage = {
  // Create a messenger for Claude
  claudeMessenger: new TBEEPMessenger('Claude-CRAS', {
    reasoningLevel: 'Deep Analysis',
    confidenceDefault: 'High'
  }),
  
  // Quick demo function
  demo: function() {
    console.log('📱 T-BEEP Messenger Demo\n');
    
    const msg = this.claudeMessenger.quickMessage(
      'Let\'s plan the next phase of repository development.',
      ['@ChatGPT-GPAS', '@Human-Initiator']
    );
    
    console.log('Generated Message:');
    console.log(msg);
    console.log('\n✅ Ready to copy-paste to your AI assistant!');
  }
};

// Export for use
if (typeof module !== 'undefined') {
  module.exports = { TBEEPMessenger, exampleUsage };
}

// Auto-demo for mobile testing
if (typeof window === 'undefined' && require.main === module) {
  exampleUsage.demo();
}
