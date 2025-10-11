---
id: sops.onboarding
version: 1.0
last_updated: 2025-10-10
tags: [sop, onboarding, user-management, workflow]
---

# User Onboarding SOP

## Purpose
This SOP documents the complete user onboarding workflow for the Guardian Angel League Discord Bot, covering user registration, approval processes, and role assignment.

## Scope
- New user registration and verification
- Admin approval workflows
- Role assignment and permissions management
- User data synchronization
- Onboarding troubleshooting

## Workflow Overview

### 1. User Registration
1. **Initial Interaction**: User joins Discord server
2. **Welcome Process**: Bot sends welcome message with registration instructions
3. **Information Collection**: User provides required information via slash commands
4. **Data Validation**: Bot validates user input against requirements
5. **Temporary Status**: User placed in pending/onboarding status

### 2. Admin Approval Process
1. **Review Queue**: Admins receive notification of pending users
2. **User Vetting**: Admin reviews user information and verification status
3. **Approval Decision**: Admin approves or rejects user application
4. **Status Update**: Bot updates user status based on admin decision
5. **Role Assignment**: Appropriate roles assigned to approved users

### 3. Integration Points
- **Google Sheets**: User data synchronized with master sheet
- **Riot API**: Summoner name verification for TFT players
- **Database**: Persistent storage of user status and history
- **Discord Roles**: Automatic role management based on approval status

## Required Tools and Permissions

### Bot Permissions
- `Manage Roles`: Required for role assignment
- `Send Messages`: For communication with users
- `Embed Links`: For rich formatting of onboarding messages
- `Read Message History`: For reviewing user interactions

### Admin Requirements
- Admin role with approval permissions
- Access to user management dashboard/commands
- Ability to review and edit user information

### User Requirements
- Discord account in good standing
- Required verification information (IGN, Discord ID, etc.)
- Compliance with server rules and guidelines

## Step-by-Step Process

### For New Users
1. **Join Server**: User receives the Discord server invite
2. **Read Rules**: User acknowledges server rules and guidelines
3. **Register Command**: User executes `/register` command with required information
4. **Provide Details**: User submits IGN, Discord tag, and other required fields
5. **Wait for Approval**: User receives confirmation and awaits admin review

### For Admins
1. **Monitor Queue**: Check for new pending users via `/pending-users` command
2. **Review Information**: Examine user-provided details and verification status
3. **Verify Identity**: Cross-reference user information as needed
4. **Make Decision**: Use `/approve-user` or `/reject-user` commands
5. **Document Reason**: Add notes for approval/rejection decisions

### Automated Processes
1. **Data Validation**: Bot validates user input format and completeness
2. **Duplicate Detection**: Check for existing registrations
3. **Role Management**: Automatically assign/remove roles based on status
4. **Notification System**: Alert admins of new pending users
5. **Data Synchronization**: Update Google Sheets and database records

## Data Management

### Information Collected
- Discord User ID and username
- In-Game Name (IGN) and verification status
- Registration timestamp
- Approval status and decision details
- Role assignments and permissions

### Storage Locations
- **Database**: Primary storage with full user history
- **Google Sheets**: Master list for admin review and reporting
- **Discord Roles**: Temporary status indicators

### Data Retention
- Active users: Indefinite retention with regular updates
- Rejected users: 30-day retention before deletion
- Audit logs: 90-day retention for compliance

## Troubleshooting

### Common Issues
1. **User Not Receiving Roles**: Check bot permissions and role hierarchy
2. **Verification Failures**: Validate IGN format and API connectivity
3. **Duplicate Registrations**: Use merge functionality or manual resolution
4. **Approval Delays**: Check admin notification system and availability

### Error Handling
- **Invalid Input**: Provide clear error messages and format examples
- **API Failures**: Implement retry logic and fallback procedures
- **Permission Issues**: Alert admins of configuration problems
- **Data Conflicts**: Use conflict resolution procedures and manual review

## Monitoring and Reporting

### Key Metrics
- Registration completion rate
- Average approval time
- Rejection rate and reasons
- User satisfaction scores

### Reports
- Daily onboarding summary
- Weekly approval statistics
- Monthly trend analysis
- Quarterly compliance review

## Security Considerations

### Data Protection
- Encrypt sensitive user information
- Limit access to user data to authorized admins
- Regular security audits of user data handling

### Access Control
- Role-based permissions for approval workflows
- Audit trail of all approval decisions
- Multi-factor authentication for admin actions

## Compliance Requirements

### Discord Terms of Service
- Ensure compliance with Discord user data policies
- Provide opt-out mechanisms for data collection
- Maintain transparency about data usage

### Data Privacy
- GDPR compliance for EU users
- Data retention policies and procedures
- User consent management

## Integration Dependencies

### Required Systems
- Discord API for user and role management
- Google Sheets API for data synchronization
- Riot Games API for IGN verification
- Database for persistent storage

### Optional Integrations
- External authentication providers
- Third-party verification services
- Analytics and reporting tools

## Maintenance and Updates

### Regular Tasks
- Review and update onboarding questions
- Validate integration API connectivity
- Update role assignments and permissions
- Refresh documentation and user guides

### Scheduled Maintenance
- Monthly: Review onboarding metrics and optimize process
- Quarterly: Update integration APIs and authentication
- Annually: Comprehensive review and workflow redesign

## Documentation and Training

### User Guides
- New user registration instructions
- Admin approval workflow documentation
- Troubleshooting guides for common issues

### Training Materials
- Admin training for approval workflows
- User onboarding best practices
- Security and privacy compliance training

## Contact and Support

### Technical Support
- Bot administrator for technical issues
- Discord server moderators for user issues
- Development team for feature requests and bug reports

### Process Questions
- Server leadership for policy questions
- Admin team for workflow clarification
- Community managers for user experience feedback

---

**Version**: 1.0  
**Last Updated**: 2025-10-10  
**Next Review**: 2025-12-10  
**Maintained By**: Guardian Angel League Development Team
