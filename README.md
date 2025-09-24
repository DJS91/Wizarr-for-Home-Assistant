# Wizarr for Home Assistant

A comprehensive Home Assistant custom integration for monitoring your Wizarr server with invitation emailing capabilities.

## Features

### 📊 Sensors
- **Status Sensor**: Overall system status and statistics
- **Users Sensor**: User count and breakdown by server type
- **Invitations Sensor**: Invitation count and status breakdown  
- **Libraries Sensor**: Library count and server distribution
- **Servers Sensor**: Server count and type breakdown
- **API Keys Sensor**: API key count and status

### 🎯 Actions
- **Create Invitation**: Generate new invitation links with comprehensive options
- **Send Invitation Email**: Create invitation and send beautiful HTML emails with dynamic server information

### 📧 Email Features
- **Responsive HTML Design**: Professional, responsive email templates with modern styling
- **Dynamic Server Information**: Personalized messages using actual server names and types
- **Universal Compatibility**: Works perfectly in Outlook, Gmail, Apple Mail, and all email clients
- **Public URL Replacement**: Option to replaces internal IPs with your public server address
- **Smart Formatting**: Includes invitation details, expiration info, and access levels

## Installation

### HACS (Recommended)
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=DJS91&repository=Wizarr&category=Integration)

### Manual
1. Copy the `wizarr` folder to your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Go to **Settings** > **Devices & Services**
4. Click **Add Integration** and search for "Wizarr"
5. Enter your Wizarr server URL and API key

## Configuration

### Install config
- **Base URL**: Your Wizarr server URL (e.g., `http://192.168.1.29:5690`)
- **API Key**: Your Wizarr API key (get this from Wizarr settings)
- **Name**: Friendly name for your Wizarr instance (optional)

### Optional Settings  
- **Update Interval**: How often to poll the API (default: 30 seconds, minimum: 10 seconds)

## Usage

### Sensors
All sensors provide detailed attributes with the full API response data, plus processed summaries:

```yaml
# Example sensor data
sensor.wizarr_users:
  state: 15
  attributes:
    total_users: 15
    users_by_server:
      plex: 10
      jellyfin: 5
    raw_data: {...}
```

### Services

#### Create Invitation (no email)
```yaml
service: wizarr.create_invitation
data:
  server_ids: "1,2"                    # Required: Comma-separated server IDs
  expires_in_days: 7                   # Optional: Days until expiration
  duration: "30"                       # Optional: User access duration or "unlimited"
  library_ids: "1,3,5"                 # Optional: Restrict to specific libraries
  allow_downloads: true                # Optional: Allow downloads (default: false)
  allow_live_tv: true                  # Optional: Allow live TV (default: false)  
  allow_mobile_uploads: false          # Optional: Allow mobile uploads (default: false)
```

#### Send Invitation Email (Creates and sends with default options)
```yaml
service: wizarr.send_invitation_email
data:
  recipient_email: "user@example.com"
  server_ids: "1"
  smtp_server: "smtp.gmail.com"
  smtp_port: 587
  smtp_username: "your_email@gmail.com"
  smtp_password: "your_app_password"
```

#### Send Invitation Email (Creates and sends with options)
```yaml
service: wizarr.send_invitation_email
data:
  recipient_email: "user@example.com"
  server_ids: "1,2"
  public_url: "https://invites.yourdomain.com"  # Replaces internal IP in links
  smtp_server: "smtp.gmail.com"
  smtp_port: 587
  smtp_username: "your_email@gmail.com"
  smtp_password: "your_app_password"
  subject: "Welcome to Our Media Server!"       # Custom email subject
  expires_in_days: 7                            # Optional invitation settings
  duration: "unlimited"
  library_ids: "1,2,3"
  allow_downloads: true
  allow_live_tv: true
  allow_mobile_uploads: false
```

### 📧 Email Features Explained

#### Public URL Replacement when using email action
The `public_url` parameter automatically transforms internal invitation URLs:
- **Without public_url**: `http://192.168.1.29:5690/j/ABC123`
- **With public_url**: `https://invites.yourdomain.com/j/ABC123`

This ensures users can access invitations from external networks.

#### Dynamic Server Information
Emails automatically include personalized information:
- **Server Detection**: "You have been invited to join the **Danflix Plex** server!"
- **Access Details**: Shows expiration, library access, and permissions
- **Professional Design**: Beautiful HTML emails that work in all clients

#### Email Template Features
- 🎨 **Modern Design**: Gradient headers, styled buttons, organized layouts
- 📱 **Mobile Responsive**: Perfect display on phones, tablets, and desktop
- 🔧 **Universal Compatibility**: Works in Outlook, Gmail, Apple Mail, Thunderbird
- ✨ **Rich Content**: Server info, invitation details, and clear call-to-action buttons

### Events
The integration fires events when actions complete:
- `wizarr_invitation_created`: When an invitation is created
- `wizarr_invitation_email_sent`: When an invitation email is sent successfully

### Example Automation
```yaml
automation:
  - alias: "Send Wizarr invitation on new user request"
    trigger:
      - platform: state
        entity_id: input_boolean.send_invitation
        to: 'on'
    action:
      - service: wizarr.send_invitation_email
        data:
          recipient_email: "{{ states('input_text.user_email') }}"
          server_ids: "1"
          public_url: "https://invites.yourdomain.com"
          smtp_server: "smtp.gmail.com"
          smtp_port: 587
          smtp_username: "{{ states('input_text.smtp_username') }}"
          smtp_password: "{{ states('input_text.smtp_password') }}"
          expires_in_days: 7
          allow_downloads: true
```

## 📡 API Coverage

This integration covers all major Wizarr API endpoints:
- **GET /status** - System statistics and version info
- **GET /users** - User management data
- **GET /invitations** - Invitation tracking
- **GET /libraries** - Available libraries
- **GET /servers** - Connected media servers
- **GET /api-keys** - API key management
- **POST /invitations** - Create new invitations

## 🔧 Advanced Configuration

### Server IDs
Find your server IDs in the Wizarr admin panel or check the `wizarr_servers` sensor attributes.

### Library IDs  
Check the `wizarr_libraries` sensor attributes for available library IDs to restrict access.

## ❓ Support

### Troubleshooting
For issues with this integration, please check:
1. **Network Access**: Your Wizarr server is accessible from Home Assistant
2. **API Key**: Your API key is valid and has appropriate permissions
3. **Logs**: Check Home Assistant logs for detailed error messages
4. **Email Issues**: Verify SMTP settings and authentication (use App Passwords for Gmail/Outlook)

### Common Issues
- **"No invitation URL received"**: Check your API key permissions and server connectivity
- **Email not sending**: Verify SMTP credentials and use App Passwords for major providers
- **Internal URLs in emails**: Use the `public_url` parameter to replace with your domain

## 📄 License

This integration is provided as-is for Home Assistant users. Built for the Wizarr community.

---

**Version**: 1.0.0  
**Compatibility**: Home Assistant 2024.1+  

**Wizarr API**: v2.2.1+
