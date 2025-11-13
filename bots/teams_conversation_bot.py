# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import os
import json
import logging
from datetime import datetime

from botbuilder.core import CardFactory, TurnContext, MessageFactory
from botbuilder.core.teams import TeamsActivityHandler
from botbuilder.schema import CardAction, HeroCard
from botbuilder.schema.teams import TeamInfo, TeamsChannelAccount
from botbuilder.schema._connector_client_enums import ActionTypes

from agent_framework import MCPStreamableHTTPTool
from agent_framework.azure import AzureOpenAIChatClient

from dotenv import load_dotenv

load_dotenv()

# Configure logger
logger = logging.getLogger(__name__)

ADAPTIVECARDTEMPLATE = "resources/UserMentionCardTemplate.json"

# tool = MCPStreamableHTTPTool(
#     name="Microsoft Learn MCP",
#     url="https://learn.microsoft.com/api/mcp",
#     # we don't require approval for microsoft_docs_search tool calls
#     # but we do for any other tool
#     # approval_mode={"never_require_approval": ["microsoft_docs_search"]},
# )

tool = MCPStreamableHTTPTool(
    name="MS Graph",
    url="http://localhost:8000/mcp",
    # we don't require approval for microsoft_docs_search tool calls
    # but we do for any other tool
    # approval_mode={"never_require_approval": ["microsoft_docs_search"]},
)

llm = AzureOpenAIChatClient(
    endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT", ""),
    deployment_name=os.environ.get("AZURE_OPENAI_MODEL", ""),
    api_key=os.environ.get("AZURE_OPENAI_API_KEY", ""),
)


agent = llm.create_agent(
    name="test_agent",
    instructions="You are a helpful agent. You use Model Context Protocol (MCP) tools to answer user questions. "
    "You can only respond using the tools available to you. Do not make up tool functionality. The tools will be"
    "Provided to you in the prompt.",
    tools=[tool],
)

thread = agent.get_new_thread()


class TeamsConversationBot(TeamsActivityHandler):
    conversation_references = {}

    def __init__(self, app_id: str, app_password: str):
        self._app_id = app_id
        self._app_password = app_password
        logger.info("TeamsConversationBot initialized with app_id: %s", app_id)

    async def on_teams_members_added(  # pylint: disable=unused-argument
        self,
        teams_members_added: list[TeamsChannelAccount],
        team_info: TeamInfo,
        turn_context: TurnContext,
    ):
        logger.info(
            "New members added to team: %s", [m.name for m in teams_members_added]
        )
        for member in teams_members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity(f"Welcome to the team {member.name}. ")

    async def on_message_activity(self, turn_context: TurnContext):
        logger.info(f"Message activity received: {turn_context.activity.from_property}")
        # TurnContext.remove_recipient_mention(turn_context.activity)
        text = turn_context.activity.text.strip().lower()

        logger.info(
            "Received message: '%s' from user: %s",
            text,
            turn_context.activity.from_property.name
            if turn_context.activity.from_property
            else "Unknown",
        )

        if "start_analyze_email" in text:
            logger.debug("Handling 'start_analyze_email' command")
            reply_activity = MessageFactory.text("Analyzing email...")
            await turn_context.send_activity(reply_activity)

            logger.info("Passing message to agent: '%s'", text)
            result = await agent.run(text, thread=thread)
            reply_activity = MessageFactory.text(result.text)

            await turn_context.send_activity(reply_activity)

            return
        if "get card" in text:
            logger.debug("Handling 'card' command")
            await self._send_card(turn_context)

            return

        logger.info("Passing message to agent: '%s'", text)
        result = await agent.run(text, thread=thread)

        # Pretty print the agent result
        try:
            json_obj = json.loads(result.to_json())
            pretty_json = json.dumps(json_obj, indent=2)
            logger.info("Agent result (JSON):\n%s", pretty_json)
        except (json.JSONDecodeError, Exception) as e:
            logger.info("Agent result: %s", result.to_json())
            logger.debug("Failed to pretty print result: %s", e)

        logger.info("Agent response: '%s'", result.text)
        reply_activity = MessageFactory.text(result.text)

        await turn_context.send_activity(reply_activity)

        return

    async def _send_card(self, turn_context: TurnContext):
        buttons = [
            CardAction(
                type=ActionTypes.message_back,
                title="Analyze Email",  # this is the button text shown to user
                text="start_analyze_email",  # this text is not displayed to user, it is sent back to bot when button is clicked
            ),
        ]

        # Determine greeting based on current time
        current_hour = datetime.now().hour
        if current_hour < 12:
            greeting = f"Good morning, {turn_context.activity.from_property.name}"
        elif current_hour < 18:
            greeting = f"Good afternoon, {turn_context.activity.from_property.name}"
        else:
            greeting = f"Good evening, {turn_context.activity.from_property.name}"

        card = HeroCard(
            title=greeting,
            text="Use the Buttons to perform Actions or type your own message to interact with the agent.  I will use the tools at my disposal to assist you.",
            buttons=buttons,
        )
        await turn_context.send_activity(
            MessageFactory.attachment(CardFactory.hero_card(card))
        )
