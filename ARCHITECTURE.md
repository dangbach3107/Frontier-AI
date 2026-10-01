# Architecture note

## Core principle

Data minimization:
LLM chỉ nhận phần thông tin tối thiểu cần thiết để tạo content.

## Control points

1. Input layer
   - structured questions
   - explicit consent options

2. Pre-processing
   - regex/rule detection
   - PII detection
   - business-sensitive classification
   - block/mask/flag

3. LLM
   - receives sanitized input
   - strict system policy: never reconstruct masked data

4. Output guardrail
   - scan PII
   - scan credentials
   - scan business-sensitive claims
   - claim/quality validation

5. Human control
   - learner review
   - consent
   - Datapot approval

6. Publishing
   - website/social

7. Monitoring
   - share rate
   - learner effort
   - approval rate
   - time-to-publish
   - content reuse rate