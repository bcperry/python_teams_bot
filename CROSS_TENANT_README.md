# Cross-Tenant Bot Authentication

This document explains how the Teams bot handles authentication when it's hosted in one Azure tenant but used by Teams users in a different tenant.

## Scenario Overview

- **Tenant A**: Alex's tenant (where Teams users interact with the bot)
- **Tenant B**: Blaine's tenant (where the bot is registered and hosted in Azure)
- **Bot Registration**: The bot's Azure AD app is registered in **Tenant B** (Blaine's tenant)
- **Teams Environment**: Users interact with the bot from **Tenant A** (Alex's tenant)
- **Bot Service**: Hosted in Azure in **Tenant B** (Blaine's tenant)

## How Cross-Tenant Authentication Works

### 1. Bot-to-Microsoft Authentication (Tenant B - Blaine's Tenant)

When the bot service starts up:
- It authenticates to the **Azure Bot Service** using `app_id` and `app_password` from Tenant B (Blaine's tenant)
- This gives the bot permission to receive and send messages through the Bot Framework
- The bot establishes its identity as a trusted application

### 2. Teams Sends Activity Payload (Tenant A - Alex's Tenant)

When a user in Tenant A (Alex's tenant) messages the bot, Teams sends an Activity object containing:

```python
turn_context.activity.from_property.id              # User's Teams user ID
turn_context.activity.from_property.name            # User's display name
turn_context.activity.from_property.aad_object_id   # User's Azure AD object ID in Tenant A (Alex's)
turn_context.activity.tenant.id                     # Tenant A's ID (Alex's)
turn_context.activity.conversation.id               # The conversation ID
```

### 3. Bot Framework Validates the Request

- The Bot Framework validates that the incoming activity is genuinely from Microsoft Teams using JWT tokens
- This cryptographic validation ensures the user information in the payload is trustworthy
- The bot doesn't need to authenticate the user directly—Teams already did that in Tenant A (Alex's tenant)

### 4. Bot Accesses User Information

In the code, when you call `TeamsInfo.get_member()`:

```python
member = await TeamsInfo.get_member(
    turn_context, turn_context.activity.from_property.id
)
```

The bot:
- Uses the `TurnContext` to make a **service-to-service call** back to Microsoft Teams
- Authenticates this call using its own credentials (from Tenant B - Blaine's tenant)
- Teams responds with the user's details from **Tenant A** (Alex's tenant) because the bot is asking about a specific conversation it's already part of

## What the Bot CAN Do (Without Additional Auth)

The bot has access to:

✅ User's name, Teams user ID, and AAD object ID (from the activity payload)  
✅ Ability to send messages to users in the conversation  
✅ Ability to read messages sent to it  
✅ Roster information for Teams/channels it's added to  
✅ Conversation metadata and channel information  

## What the Bot CANNOT Do (Without Additional Auth)

The bot does **not** have access to:

❌ User's OneDrive, Outlook, or other Microsoft Graph resources in Tenant A (Alex's tenant)  
❌ User's email or calendar  
❌ SharePoint sites in Tenant A  
❌ Ability to perform actions on the user's behalf outside of Teams conversations  
❌ Access to resources in Tenant A beyond the conversation scope  

## Key Security Points

### No User Credentials Needed
- The bot never asks for user passwords or OAuth tokens for basic functionality
- User authentication happens entirely within Teams (Tenant A - Alex's tenant)

### Teams Vouches for Identity
- Teams has already authenticated the user in Tenant A (Alex's tenant)
- The verified identity is included in the activity payload
- The Bot Framework cryptographically validates all messages

### Limited Scope by Design
- The bot can only see information about conversations it's part of
- It cannot browse Tenant A's directory or access resources outside Teams
- This is enforced by the Teams API and Bot Framework

### Cross-Tenant Trust Model
- Microsoft Teams trusts properly registered bots from any tenant
- The Bot Framework validates all messages to prevent spoofing
- The bot's credentials (from Tenant B - Blaine's tenant) only grant access to Bot Framework APIs
- Access to Tenant A resources is mediated through Teams, not direct API calls

## Adding User Authentication (Optional)

If you need the bot to access other Microsoft Graph resources in Tenant A (Alex's tenant) (like reading a user's calendar, accessing OneDrive, etc.), you must implement **OAuth authentication with user consent**:

### High-Level Steps:
1. Configure OAuth connection in the Azure Bot Service
2. Add Microsoft Graph API permissions to the bot's app registration
3. Implement sign-in flow using OAuthPrompt or SSO
4. Request user consent for the required scopes
5. Obtain and use delegated access tokens

### Example Use Cases:
- Reading user's email (Mail.Read)
- Sending emails on behalf of the user (Mail.Send)
- Accessing user's calendar (Calendars.Read, Calendars.ReadWrite)
- Accessing OneDrive files (Files.Read, Files.ReadWrite)
- Accessing SharePoint documents
- Reading user profile information (User.Read)

---

## Implementing OAuth for Cross-Tenant Access

Here's a detailed walkthrough for implementing OAuth to access resources like **email in Alex's tenant** (Tenant A) from a bot registered in **Blaine's tenant** (Tenant B).

### Part 1: App Registration Configuration (Tenant B - Blaine's Tenant)

Your bot's Azure AD app registration lives in **Tenant B** (Blaine's tenant), but it needs to request delegated permissions to access resources in **Tenant A** (Alex's tenant).

#### 1.1: Configure Multi-Tenant Support

1. Go to the [Azure Portal](https://portal.azure.com) and navigate to **Azure Active Directory** > **App registrations**
2. Select your bot's app registration (the one created when you registered the Azure Bot)
3. Go to **Authentication** in the left menu
4. Under **Supported account types**, ensure you have selected:
   - **Accounts in any organizational directory (Any Azure AD directory - Multitenant)**
   - OR **Accounts in any organizational directory and personal Microsoft accounts** (if you need personal account support)

> **Note**: This allows users from other tenants (like Alex's) to authenticate and consent to your bot.

#### 1.2: Add Redirect URIs

The redirect URI is where users are sent after authentication. For Azure Bot Service, add these redirect URIs:

1. Still in the **Authentication** section, click **Add a platform** > **Web**
2. Add the Bot Framework redirect URIs:
   ```
   https://token.botframework.com/.auth/web/redirect
   ```
3. For local development/testing, you may also add:
   ```
   https://localhost
   ```
4. Click **Save**

#### 1.3: Add Microsoft Graph API Permissions

Now configure the delegated permissions your bot needs to access user resources:

1. Go to **API permissions** in the left menu
2. Click **Add a permission**
3. Select **Microsoft Graph**
4. Choose **Delegated permissions** (not Application permissions)
5. Add the permissions you need. For email access, add:
   - `Mail.Read` - Read user mail
   - `Mail.Send` - Send mail as a user
   - `User.Read` - Sign in and read user profile (typically already present)
   - `offline_access` - Maintain access to data (for refresh tokens)
   - `openid` - Sign users in
   - `profile` - View users' basic profile

6. Click **Add permissions**

> **Important**: For cross-tenant scenarios, you typically do NOT need to grant admin consent in Tenant B (Blaine's tenant). Users in Tenant A (Alex's tenant) will consent when they sign in.

#### 1.4: Create a Client Secret

1. Go to **Certificates & secrets** in the left menu
2. Under **Client secrets**, click **New client secret**
3. Add a description (e.g., "Bot OAuth Secret")
4. Choose an expiration period (recommended: 24 months maximum for production)
5. Click **Add**
6. **Copy the secret value immediately** - you won't be able to see it again
7. Save this securely - you'll need it for the OAuth connection configuration

### Part 2: Azure Bot Service OAuth Configuration (Tenant B - Blaine's Tenant)

Configure the OAuth connection settings in your Azure Bot resource (registered in Blaine's tenant):

#### 2.1: Add OAuth Connection Settings

1. In the [Azure Portal](https://portal.azure.com), navigate to your **Azure Bot** resource
2. Go to **Configuration** under **Settings**
3. Click **Add OAuth Connection Settings**
4. Fill in the form:

   **Connection Name**: Choose a name (e.g., `GraphConnection` or `EmailAuth`)
   - You'll reference this name in your Python code
   
   **Service Provider**: Select **Azure Active Directory v2**
   
   **Client ID**: Enter the **Application (client) ID** from your app registration
   
   **Client Secret**: Enter the **client secret** you created in step 1.4
   
   **Token Exchange URL**: Leave blank for standard OAuth (only used for SSO scenarios)
   
   **Tenant ID**: Enter **`common`** (this is critical for multi-tenant scenarios!)
   - `common` allows users from any tenant to authenticate
   - Do NOT use your specific tenant ID from Tenant B (Blaine's tenant)
   
   **Scopes**: Enter a space-separated list of the permissions you configured:
   ```
   openid profile offline_access User.Read Mail.Read Mail.Send
   ```

5. Click **Save**
6. After saving, click **Test Connection** to verify the configuration
   - This will prompt you to sign in and test the OAuth flow

### Part 3: User Consent in Tenant A (Alex's Tenant)

When a user from Tenant A (Alex's tenant) first authenticates with your bot, they'll need to consent to the permissions.

#### 3.1: User Consent Flow

**For regular users** (non-admin permissions):
- The user will see a consent dialog when they first sign in
- They can grant consent themselves for permissions that don't require admin approval
- Examples: `User.Read`, `Mail.Read`, `Mail.Send`, `Calendars.Read`

**For admin-only permissions**:
- Some permissions require tenant admin consent
- Examples: `Mail.ReadWrite.All`, `User.Read.All`, `Directory.Read.All`
- A tenant admin in Tenant A (Alex's tenant) must consent on behalf of all users

#### 3.2: Admin Consent URL (If Needed)

If your bot requires admin-only permissions, an admin in Tenant A (Alex's tenant) can grant consent by visiting this URL:

```
https://login.microsoftonline.com/{TENANT_A_ID}/adminconsent
  ?client_id={YOUR_CLIENT_ID}
  &redirect_uri={YOUR_REDIRECT_URI}
  &scope=https://graph.microsoft.com/Mail.Read https://graph.microsoft.com/Mail.Send
```

Replace:
- `{TENANT_A_ID}` - The tenant ID of Alex's tenant
- `{YOUR_CLIENT_ID}` - Your bot's application (client) ID (from Blaine's tenant)
- `{YOUR_REDIRECT_URI}` - URL-encoded redirect URI (e.g., `https%3A%2F%2Ftoken.botframework.com%2F.auth%2Fweb%2Fredirect`)

### Part 4: Python Code Implementation

Now implement the OAuth flow in your bot code using the Bot Framework SDK.

#### 4.1: Install Required Packages

Ensure you have the necessary packages:

```bash
pip install botbuilder-core botbuilder-schema botbuilder-dialogs
```

#### 4.2: Update Configuration

Add the OAuth connection name to your `config.py`:

```python
import os

class DefaultConfig:
    """Bot Configuration"""

    PORT = 3978
    APP_ID = os.environ.get("MicrosoftAppId", "")
    APP_PASSWORD = os.environ.get("MicrosoftAppPassword", "")
    
    # OAuth Configuration
    CONNECTION_NAME = os.environ.get("ConnectionName", "GraphConnection")
```

And in your `.env` file:

```
MicrosoftAppId=<your-app-id>
MicrosoftAppPassword=<your-app-password>
ConnectionName=GraphConnection
```

#### 4.3: Implement OAuth in Your Bot

Here's how to add OAuth authentication to your bot:

```python
from botbuilder.core import MessageFactory, TurnContext
from botbuilder.core.teams import TeamsActivityHandler
from botbuilder.schema import Activity, ActivityTypes
from botbuilder.dialogs import Dialog, DialogSet, DialogTurnStatus, WaterfallDialog, WaterfallStepContext
from botbuilder.dialogs.prompts import OAuthPrompt, OAuthPromptSettings, PromptOptions
from botbuilder.core import ConversationState, UserState
import requests

class TeamsConversationBot(TeamsActivityHandler):
    def __init__(
        self, 
        app_id: str, 
        app_password: str,
        connection_name: str,
        conversation_state: ConversationState
    ):
        self._app_id = app_id
        self._app_password = app_password
        self._connection_name = connection_name
        self._conversation_state = conversation_state
        
        # Create dialog set
        self._dialogs = DialogSet(conversation_state.create_property("DialogState"))
        
        # Add OAuth prompt
        self._dialogs.add(
            OAuthPrompt(
                "OAuthPrompt",
                OAuthPromptSettings(
                    connection_name=connection_name,
                    text="Please sign in to access your email",
                    title="Sign In",
                    timeout=300000  # 5 minutes
                )
            )
        )
        
    async def on_message_activity(self, turn_context: TurnContext):
        # Save any state changes
        await self._conversation_state.save_changes(turn_context, False)
        
        # Create dialog context
        dialog_context = await self._dialogs.create_context(turn_context)
        
        # Continue the dialog or start a new one
        results = await dialog_context.continue_dialog()
        
        if results.status == DialogTurnStatus.Empty:
            # Check if user wants to access email
            text = turn_context.activity.text.strip().lower()
            
            if "email" in text or "mail" in text:
                # Start OAuth prompt
                await dialog_context.begin_dialog("OAuthPrompt")
            else:
                # Normal message handling
                await turn_context.send_activity(f"You said: {text}")
        
        elif results.status == DialogTurnStatus.Complete:
            # OAuth completed successfully
            token_response = results.result
            
            if token_response and token_response.token:
                # Use the token to access Microsoft Graph
                await self._use_token(turn_context, token_response.token)
            else:
                await turn_context.send_activity("Login was not successful.")
        
        # Save conversation state
        await self._conversation_state.save_changes(turn_context, False)
    
    async def on_token_response_event(self, turn_context: TurnContext):
        """Handle token response events"""
        dialog_context = await self._dialogs.create_context(turn_context)
        await dialog_context.continue_dialog()
        await self._conversation_state.save_changes(turn_context, False)
    
    async def _use_token(self, turn_context: TurnContext, token: str):
        """Use the access token to call Microsoft Graph"""
        try:
            # Call Microsoft Graph to get user's email
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            # Get user's messages
            response = requests.get(
                'https://graph.microsoft.com/v1.0/me/messages?$top=5',
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                messages = data.get('value', [])
                
                if messages:
                    reply = "Here are your recent emails:\n\n"
                    for msg in messages:
                        subject = msg.get('subject', 'No subject')
                        sender = msg.get('from', {}).get('emailAddress', {}).get('name', 'Unknown')
                        reply += f"- **{subject}** from {sender}\n"
                    
                    await turn_context.send_activity(reply)
                else:
                    await turn_context.send_activity("You have no recent emails.")
            else:
                await turn_context.send_activity(
                    f"Failed to retrieve emails. Status: {response.status_code}"
                )
        
        except Exception as e:
            await turn_context.send_activity(f"Error accessing email: {str(e)}")
```

#### 4.4: Update app.py

Update your `app.py` to include ConversationState:

```python
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, MemoryStorage, ConversationState
from botbuilder.schema import Activity
from aiohttp import web
from config import DefaultConfig
from bots.teams_conversation_bot import TeamsConversationBot

# Create adapter
SETTINGS = BotFrameworkAdapterSettings(
    DefaultConfig.APP_ID, 
    DefaultConfig.APP_PASSWORD
)
ADAPTER = BotFrameworkAdapter(SETTINGS)

# Create conversation state with memory storage
MEMORY = MemoryStorage()
CONVERSATION_STATE = ConversationState(MEMORY)

# Create the bot
BOT = TeamsConversationBot(
    DefaultConfig.APP_ID,
    DefaultConfig.APP_PASSWORD,
    DefaultConfig.CONNECTION_NAME,
    CONVERSATION_STATE
)

# Listen for incoming requests
async def messages(req: web.Request) -> web.Response:
    body = await req.json()
    activity = Activity().deserialize(body)
    auth_header = req.headers.get("Authorization", "")
    
    response = await ADAPTER.process_activity(activity, auth_header, BOT.on_turn)
    
    if response:
        return web.json_response(data=response.body, status=response.status)
    return web.Response(status=201)

# Create and start the app
APP = web.Application()
APP.router.add_post("/api/messages", messages)

if __name__ == "__main__":
    web.run_app(APP, host="localhost", port=DefaultConfig.PORT)
```

### Part 5: Testing the Cross-Tenant OAuth Flow

#### 5.1: Test Flow

1. Deploy your bot to Azure or run it locally with a tunnel (ngrok or dev tunnel)
2. Install the bot in Teams in Tenant A (Alex's tenant)
3. As a user in Tenant A (Alex's tenant), send a message containing "email" to the bot
4. The bot will respond with an OAuth sign-in card
5. Click "Sign In" and authenticate with your Tenant A (Alex's tenant) credentials
6. Review and accept the consent dialog showing the requested permissions
7. After successful authentication, the bot will use the token to access your email
8. The bot displays your recent emails from Tenant A (Alex's tenant)

#### 5.2: Token Storage

The Bot Framework Token Service automatically stores and manages tokens for you:
- Tokens are encrypted and stored securely
- Refresh tokens are used to obtain new access tokens automatically
- You can retrieve tokens without re-prompting the user (if still valid)

### Reference Documentation

- [Bot authentication in Teams](https://learn.microsoft.com/microsoftteams/platform/bots/how-to/authentication/authentication)
- [Add authentication to Teams bot](https://learn.microsoft.com/microsoftteams/platform/bots/how-to/authentication/add-authentication)
- [Microsoft identity platform OAuth 2.0 authorization code flow](https://learn.microsoft.com/azure/active-directory/develop/v2-oauth2-auth-code-flow)
- [Microsoft Graph permissions reference](https://learn.microsoft.com/graph/permissions-reference)
- [Single sign-on (SSO) for bots](https://learn.microsoft.com/microsoftteams/platform/bots/how-to/authentication/bot-sso-overview)

## Multi-Tenant Bot Registration

For production scenarios where the bot needs to work across multiple tenants:

1. **Multi-tenant App Registration**: Configure the Azure AD app as multi-tenant in Tenant B (Blaine's tenant)
2. **Admin Consent**: Each tenant (including Tenant A - Alex's tenant) must grant admin consent for the bot
3. **Teams App Catalog**: The bot can be published to:
   - Organization's app catalog (single tenant)
   - Microsoft Teams store (all tenants)
   - Custom deployment (sideloading)

## Security Best Practices

1. **Validate all inputs**: Never trust user input, even though it comes through Teams
2. **Use secure storage**: Store conversation data and user preferences securely
3. **Implement rate limiting**: Protect against abuse
4. **Log security events**: Monitor for suspicious activity
5. **Minimize permissions**: Only request Graph API permissions you actually need
6. **Regular updates**: Keep the Bot Framework SDK and dependencies updated

## Troubleshooting Cross-Tenant Issues

### Bot doesn't respond to users in Tenant A
- Verify the bot is installed in the Teams environment (Tenant A - Alex's tenant)
- Check that the messaging endpoint is publicly accessible
- Review bot service logs for authentication errors

### "MemberNotFoundInConversation" errors
- Ensure the user is actually part of the conversation
- Verify the bot has been added to the team/chat
- Check that the conversation reference is current

### Permission errors when calling Graph APIs
- Verify OAuth authentication is implemented
- Check that users in Tenant A (Alex's tenant) have granted consent
- Ensure the app registration in Tenant B (Blaine's tenant) has the required API permissions

## Code Examples

### Getting User Information (No Auth Required)
```python
async def _get_member(self, turn_context: TurnContext):
    try:
        member = await TeamsInfo.get_member(
            turn_context, turn_context.activity.from_property.id
        )
        await turn_context.send_activity(f"You are: {member.name}")
    except Exception as e:
        if "MemberNotFoundInConversation" in e.args[0]:
            await turn_context.send_activity("Member not found.")
        else:
            raise
```

### Accessing Tenant Information
```python
# The tenant where the user is located (Tenant A - Alex's tenant)
user_tenant_id = turn_context.activity.tenant.id

# User's Azure AD object ID in their tenant (Tenant A - Alex's tenant)
user_aad_id = turn_context.activity.from_property.aad_object_id
```

## Summary

Cross-tenant bot functionality works seamlessly because:
1. **Teams handles user authentication** in Tenant A (Alex's tenant)
2. **Bot Framework validates** message authenticity cryptographically
3. **Bot uses its own credentials** (from Tenant B - Blaine's tenant) to access Bot Framework APIs
4. **Teams mediates access** to user information in Tenant A (Alex's tenant) based on conversation context
5. **No direct access** to Tenant A resources without explicit user consent via OAuth

This architecture enables secure, scalable multi-tenant bot scenarios while maintaining strong security boundaries between tenants.
