# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import os
import json
import logging

from typing import List
from botbuilder.core import CardFactory, TurnContext, MessageFactory
from botbuilder.core.teams import TeamsActivityHandler, TeamsInfo
from botbuilder.schema import CardAction, HeroCard, Mention, Activity
from botbuilder.schema.teams import TeamInfo, TeamsChannelAccount
from botbuilder.schema._connector_client_enums import ActionTypes

from agent_framework import MCPStreamableHTTPTool
from agent_framework.azure import AzureOpenAIChatClient

from dotenv import load_dotenv

load_dotenv()

# Configure logger
logger = logging.getLogger(__name__)

ADAPTIVECARDTEMPLATE = "resources/UserMentionCardTemplate.json"

tool = MCPStreamableHTTPTool(
    name="Microsoft Learn MCP",
    url="https://learn.microsoft.com/api/mcp",
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
        TurnContext.remove_recipient_mention(turn_context.activity)
        text = turn_context.activity.text.strip().lower()

        logger.info(
            "Received message: '%s' from user: %s",
            text,
            turn_context.activity.from_property.name
            if turn_context.activity.from_property
            else "Unknown",
        )

        if "mention me" in text:
            logger.debug("Handling 'mention me' command")
            await self._mention_adaptive_card_activity(turn_context)
            return

        if "mention" in text:
            logger.debug("Handling 'mention' command")
            await self._mention_activity(turn_context)
            return

        if "update" in text:
            logger.debug("Handling 'update' command")
            await self._send_card(turn_context, True)
            return

        if "message" in text:
            logger.debug("Handling 'message' command - messaging all members")
            # Save the conversation reference for proactive messaging
            conversation_reference = TurnContext.get_conversation_reference(
                turn_context.activity
            )
            user_id = turn_context.activity.from_property.id
            TeamsConversationBot.conversation_references[user_id] = (
                conversation_reference
            )

            await self._message_all_members(turn_context)
            return

        if "who" in text:
            logger.debug("Handling 'who' command")
            await self._get_member(turn_context)
            return

        if "delete" in text:
            logger.debug("Handling 'delete' command")
            await self._delete_card_activity(turn_context)
            return
        if "test" in text:
            logger.debug("Handling 'test' command")
            reply_activity = MessageFactory.text("back to you")
            await turn_context.send_activity(reply_activity)
            return

        await self._send_card(turn_context, False)
        logger.info("Passing message to agent: '%s'", text)
        result = await agent.run(text, thread=thread)
        logger.info("Agent response: '%s'", result.text)
        reply_activity = MessageFactory.text(result.text)

        await turn_context.send_activity(reply_activity)

        return

    async def _mention_adaptive_card_activity(self, turn_context: TurnContext):
        try:
            member = await TeamsInfo.get_member(
                turn_context, turn_context.activity.from_property.id
            )
            logger.debug("Retrieved member info for adaptive card: %s", member.name)
        except Exception as e:
            if "MemberNotFoundInConversation" in e.args[0]:
                logger.warning(
                    "Member not found in conversation: %s",
                    turn_context.activity.from_property.id,
                )
                await turn_context.send_activity("Member not found.")
                return
            else:
                logger.error("Error retrieving member info: %s", str(e))
                raise

        card_path = os.path.join(os.getcwd(), ADAPTIVECARDTEMPLATE)
        with open(card_path, "rb") as in_file:
            template_json = json.load(in_file)

        for t in template_json["body"]:
            t["text"] = t["text"].replace("${userName}", member.name)
        for e in template_json["msteams"]["entities"]:
            e["text"] = e["text"].replace("${userName}", member.name)
            e["mentioned"]["id"] = e["mentioned"]["id"].replace(
                "${userUPN}", member.user_principal_name
            )
            e["mentioned"]["id"] = e["mentioned"]["id"].replace(
                "${userAAD}", member.aad_object_id
            )
            e["mentioned"]["name"] = e["mentioned"]["name"].replace(
                "${userName}", member.name
            )

        adaptive_card_attachment = Activity(
            attachments=[CardFactory.adaptive_card(template_json)]
        )
        await turn_context.send_activity(adaptive_card_attachment)

    async def _mention_activity(self, turn_context: TurnContext):
        mention = Mention(
            mentioned=turn_context.activity.from_property,
            text=f"<at>{turn_context.activity.from_property.name}</at>",
            type="mention",
        )

        reply_activity = MessageFactory.text(f"Hello {mention.text}")
        reply_activity.entities = [Mention().deserialize(mention.serialize())]
        await turn_context.send_activity(reply_activity)

    async def _send_card(self, turn_context: TurnContext, isUpdate):
        buttons = [
            CardAction(
                type=ActionTypes.message_back,
                title="Message all members",
                text="messageallmembers",
            ),
            CardAction(type=ActionTypes.message_back, title="Who am I?", text="whoami"),
            CardAction(
                type=ActionTypes.message_back,
                title="Find me in Adaptive Card",
                text="mention me",
            ),
            CardAction(
                type=ActionTypes.message_back, title="Delete card", text="deletecard"
            ),
        ]
        if isUpdate:
            await self._send_update_card(turn_context, buttons)
        else:
            await self._send_welcome_card(turn_context, buttons)

    async def _send_welcome_card(self, turn_context: TurnContext, buttons):
        buttons.append(
            CardAction(
                type=ActionTypes.message_back,
                title="Update Card",
                text="updatecardaction",
                value={"count": 0},
            )
        )
        card = HeroCard(
            title="Welcome Card", text="Click the buttons.", buttons=buttons
        )
        await turn_context.send_activity(
            MessageFactory.attachment(CardFactory.hero_card(card))
        )

    async def _send_update_card(self, turn_context: TurnContext, buttons):
        data = turn_context.activity.value
        data["count"] += 1
        buttons.append(
            CardAction(
                type=ActionTypes.message_back,
                title="Update Card",
                text="updatecardaction",
                value=data,
            )
        )
        card = HeroCard(
            title="Updated card", text=f"Update count {data['count']}", buttons=buttons
        )

        updated_activity = MessageFactory.attachment(CardFactory.hero_card(card))
        updated_activity.id = turn_context.activity.reply_to_id
        await turn_context.update_activity(updated_activity)

    async def _get_member(self, turn_context: TurnContext):
        try:
            member = await TeamsInfo.get_member(
                turn_context, turn_context.activity.from_property.id
            )
            logger.debug("Retrieved member info: %s", member.name)
        except Exception as e:
            if "MemberNotFoundInConversation" in e.args[0]:
                logger.warning("Member not found in conversation")
                await turn_context.send_activity("Member not found.")
            else:
                logger.error("Error retrieving member info: %s", str(e))
                raise
        else:
            await turn_context.send_activity(f"You are: {member.name}")

    async def _message_all_members(self, turn_context: TurnContext):
        team_members = await self._get_paged_members(turn_context)
        logger.info("Messaging %d team members", len(team_members))

        for member in team_members:
            user_id = member.id
            conversation_reference = TeamsConversationBot.conversation_references.get(
                user_id
            )
            if conversation_reference:

                async def send_message(tc: TurnContext):
                    await tc.send_activity(
                        f"Hello {member.name}. I'm a Teams conversation bot."
                    )

                await turn_context.adapter.continue_conversation(
                    conversation_reference, send_message, self._app_id
                )
            else:
                logger.debug(
                    "No conversation reference found for user: %s", member.name
                )

        logger.info("All messages sent to team members")
        await turn_context.send_activity(
            MessageFactory.text("All messages have been sent")
        )

    async def _get_paged_members(
        self, turn_context: TurnContext
    ) -> List[TeamsChannelAccount]:
        paged_members = []
        continuation_token = None

        while True:
            current_page = await TeamsInfo.get_paged_members(
                turn_context, continuation_token, 100
            )
            continuation_token = current_page.continuation_token
            paged_members.extend(current_page.members)

            if continuation_token is None:
                break

        return paged_members

    async def _delete_card_activity(self, turn_context: TurnContext):
        await turn_context.delete_activity(turn_context.activity.reply_to_id)
