#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import os

""" Bot Configuration """


class DefaultConfig:
    """Bot Configuration"""

    PORT = int(os.environ.get("PORT", 3978))
    APP_ID = os.environ.get("MicrosoftAppId", "")
    APP_PASSWORD = os.environ.get("MicrosoftAppPassword", "")
    APP_TYPE = os.environ.get("MicrosoftAppType", "")
    APP_TENANTID = os.environ.get("MicrosoftAppTenantId", "")

    # Cloud Settings
    CLOUD_LOCATION = os.environ.get("CLOUD_LOCATION", "AzureCloud")

    if CLOUD_LOCATION != "AzureCloud":
        # Azure Government Cloud Settings
        CHANNEL_SERVICE = os.environ.get(
            "CHANNEL_SERVICE", "https://botframework.azure.us"
        )

    # for GCC-High
    # OAUTH_URL = os.environ.get("OAUTH_URL", "https://tokengcch.botframework.azure.us/")
    # TO_CHANNEL_FROM_BOT_LOGIN_URL = os.environ.get("TO_CHANNEL_FROM_BOT_LOGIN_URL", "https://login.microsoftonline.us/MicrosoftServices.onmicrosoft.us")
    # TO_CHANNEL_FROM_BOT_OAUTH_SCOPE = os.environ.get("TO_CHANNEL_FROM_BOT_OAUTH_SCOPE", "https://api.botframework.us")
    # TO_BOT_FROM_CHANNEL_TOKEN_ISSUER = os.environ.get("TO_BOT_FROM_CHANNEL_TOKEN_ISSUER", "https://api.botframework.us")
    # TO_BOT_FROM_CHANNEL_OPENID_METADATA_URL = os.environ.get("TO_BOT_FROM_CHANNEL_OPENID_METADATA_URL", "https://login.botframework.azure.us/v1/.well-known/openidconfiguration")
    # TO_BOT_FROM_EMULATOR_OPENID_METADATA_URL = os.environ.get("TO_BOT_FROM_EMULATOR_OPENID_METADATA_URL", "https://login.microsoftonline.us/cab8a31a-1906-4287-a0d8-4eef66b95f6e/v2.0/.well-known/openid-configuration")
    # VALIDATE_AUTHORITY = os.environ.get("VALIDATE_AUTHORITY", "true").lower() == "true"

    # for DOD
    # CHANNEL_SERVICE = os.environ.get("CHANNEL_SERVICE", "https://botframework.azure.us")
    # OAUTH_URL = os.environ.get("OAUTH_URL", "https://apiDoD.botframework.azure.us")
    # TO_CHANNEL_FROM_BOT_LOGIN_URL = os.environ.get("TO_CHANNEL_FROM_BOT_LOGIN_URL", "https://login.microsoftonline.us/MicrosoftServices.onmicrosoft.us")
    # TO_CHANNEL_FROM_BOT_OAUTH_SCOPE = os.environ.get("TO_CHANNEL_FROM_BOT_OAUTH_SCOPE", "https://api.botframework.us")
    # TO_BOT_FROM_CHANNEL_TOKEN_ISSUER = os.environ.get("TO_BOT_FROM_CHANNEL_TOKEN_ISSUER", "https://api.botframework.us")
    # TO_BOT_FROM_CHANNEL_OPENID_METADATA_URL = os.environ.get("TO_BOT_FROM_CHANNEL_OPENID_METADATA_URL", "https://login.botframework.azure.us/v1/.well-known/openidconfiguration")
    # TO_BOT_FROM_EMULATOR_OPENID_METADATA_URL = os.environ.get("TO_BOT_FROM_EMULATOR_OPENID_METADATA_URL", "https://login.microsoftonline.us/cab8a31a-1906-4287-a0d8-4eef66b95f6e/v2.0/.well-known/openid-configuration")
    # VALIDATE_AUTHORITY = os.environ.get("VALIDATE_AUTHORITY", "true").lower() == "true"
