# T-BEEP Protocol API Reference

## Message Format Specification

### Required Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `threadToken` | String | Unique conversation identifier | `#PROJECT_001.0` |
| `instance` | String | AI instance identifier | `Claude-CRAS` |
| `reasoningLevel` | String | Depth of analysis | `Deep Analysis` |
| `confidence` | String | Certainty level | `High/Medium/Low` |
| `collaborationMode` | String | Type of interaction | `Technical Review` |
| `timestamp` | String | ISO timestamp | `2025-05-29T10:00:00Z` |
| `version` | String | Message version | `#PROJECT.v1.0` |

### Optional Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `resources` | Array | Referenced materials | `["requirements.md", "api-spec"]` |
| `handoff` | Array | Next participants | `["@Claude", "@Human"]` |
| `content` | String | Message body | Main message content |

## Thread Token Format

**Pattern:** `#PROJECT_NAME_NUMBER.VERSION`

### Valid Examples
- `#COMM_PROTO006.0` - Communication protocol, issue 6, version 0
- `#SOFTWARE_PROJ_001.1` - Software project, issue 1, version 1  
- `#CODE_REVIEW_042.2` - Code review, issue 42, version 2

### Rules
- Must start with `#`
- Project name in UPPERCASE with underscores
- Number must be 3+ digits
- Version separated by period
- No spaces or special characters except underscore

## Reasoning Levels

### Standard Levels
- **Basic** - Simple responses, minimal detail
- **Detailed** - Comprehensive analysis with examples
- **Deep Analysis** - Thorough investigation with multiple perspectives
- **Implementation** - Focus on practical execution
- **Strategic** - High-level planning and coordination

### Specialized Levels
- **Security Analysis** - Security-focused review
- **Code Review** - Technical code evaluation
- **Research Synthesis** - Academic/research compilation
- **Creative Collaboration** - Artistic/creative partnership

## Confidence Levels

### Standard Scale
- **High** - Very certain, well-established facts
- **Medium** - Reasonable certainty, some assumptions
- **Low** - Uncertain, exploratory, needs validation

### Usage Guidelines
- Use **High** for factual information and proven methods
- Use **Medium** for analysis with reasonable assumptions
- Use **Low** for exploratory ideas and uncertain recommendations

## Collaboration Modes

### Primary Modes
- **Discussion** - Open conversation and idea exchange
- **Technical Review** - Focused technical analysis
- **Implementation** - Practical execution and building
- **Research** - Information gathering and synthesis
- **Creative** - Artistic and imaginative collaboration
- **Planning** - Strategic and tactical planning

### Specialized Modes
- **Code Review** - Software code evaluation
- **Architecture Design** - System design and planning
- **Problem Solving** - Issue resolution and debugging
- **Documentation** - Writing and editing documentation
- **Quality Assurance** - Testing and validation

## Handoff Protocol

### Format
Use `@` prefix for clear targeting: `@InstanceName`

### Common Patterns
- `@Claude-CRAS` - Hand to Claude for analysis
- `@ChatGPT-GPAS` - Hand to ChatGPT for implementation
- `@Human-Initiator` - Return to human for decision
- `@All` - Everyone should respond
- `@Next` - Continue to next in sequence

### Best Practices
- Always specify handoff targets
- Use clear, unambiguous instance names
- Include brief context for handoff reason
- Avoid handoff loops (A→B→A endlessly)

## Resource References

### Format
Array of strings describing referenced materials

### Examples
```json
"resources": [
  "project-requirements.md",
  "api-specification",
  "previous-analysis",
  "user-feedback-summary"
]
```

### Best Practices
- Use descriptive, specific names
- Include file extensions when relevant
- Reference previous thread tokens for continuity
- Keep resource names concise but clear

## Mobile Implementation Notes

### Copy-Paste Format
```
🔹 Thread Token: #PROJECT_001.0
🔹 Instance: YourAI-Instance
🧠 Reasoning Level: Detailed
📊 Confidence: Medium
🤝 Collaboration Mode: Discussion
⏰ Timestamp: 2025-05-29T10:00:00Z
🔢 Version: #PROJECT.v1.0
📎 Resources: [resource1, resource2]
🔁 Handoff: @NextAI, @Human

Your message content here...
```

### Mobile-Friendly Tips
- Use emoji headers for easy visual parsing
- Keep each field on separate line
- Use consistent spacing and formatting
- Include line breaks for readability

## Validation Rules

### Thread Token Validation
```javascript
/^#[A-Z_]+\d{3,4}\.\d+$/
```

### Required Field Check
All required fields must be present and non-empty

### Format Consistency
- Arrays must be proper JSON arrays
- Timestamps must be valid ISO format
- Confidence must be High/Medium/Low
- Instance names should be consistent

## Error Handling

### Common Issues
1. **Invalid thread token format** - Check pattern compliance
2. **Missing required fields** - Verify all required fields present
3. **Broken thread continuity** - Ensure version numbers increment
4. **Ambiguous handoffs** - Use clear, specific targeting

### Recovery Strategies
1. **Format errors** - Regenerate message with correct format
2. **Thread breaks** - Start new thread or reference previous
3. **Lost context** - Include relevant background in resources
4. **Collaboration stalls** - Explicit handoff with clear instructions

## Examples and Templates

See `/examples/` directory for complete usage examples:
- `project-planning.md` - Multi-AI project coordination
- `code-review.md` - Collaborative code analysis
- `research-synthesis.md` - Academic collaboration patterns

## Implementation Support

### Python Reference
See `implementations/reference/python/tbeep_messenger.py`

### JavaScript Reference
See `implementations/reference/javascript/tbeep-messenger.js`

### Validation Tools  
See `core/validators.js` for format checking

### Test Suite
See `tests/` directory for comprehensive testing tools
