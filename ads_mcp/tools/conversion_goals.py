# Copyright 2026 Google LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tools for managing campaign and customer conversion goals.

Conversion goals control which conversion-action categories feed into the
`metrics.conversions` column (and therefore Smart Bidding) for a given
campaign or for the whole customer account. They are pre-created by Google
Ads when a campaign exists; only the `biddable` flag is mutable through
the API. There is no create / remove operation for these resources.

Common use case: a campaign is using campaign-specific conversion goals
that override the customer-level defaults and have a category set to
non-biddable, so conversions land in `all_conversions` but never appear in
`metrics.conversions`. Flipping `biddable` to true via these tools fixes
the reporting and re-enables Smart Bidding optimization for that category.
"""

from typing import Any, Dict, List, Optional

from ads_mcp.coordinator import mcp
import ads_mcp.utils as utils


@mcp.tool()
def update_campaign_conversion_goal(
    customer_id: str,
    campaign_id: str,
    goals: List[Dict[str, Any]],
    login_customer_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Updates the `biddable` flag on one or more campaign conversion goals.

    A campaign conversion goal is identified by the tuple (campaign_id,
    category, origin). Setting `biddable=true` makes conversions in that
    category count toward the campaign's `metrics.conversions` column and
    feed Smart Bidding. Setting `biddable=false` excludes them from the
    primary metric (they still surface in `metrics.all_conversions`).

    Use this when a campaign is overriding the customer-level default
    goals (visible via the `campaign_conversion_goal` resource) and a
    category that should be primary is currently set to non-biddable.

    Args:
        customer_id: The Google Ads customer ID (numbers only, no hyphens).
        campaign_id: The ID of the campaign whose goals you want to update.
        goals: List of goal updates. Each item must be a dict with:
            - category: A ConversionActionCategory enum name. Common
              values: PURCHASE, SIGNUP, REQUEST_QUOTE, BOOK_APPOINTMENT,
              SUBMIT_LEAD_FORM, CONTACT, ENGAGEMENT, DEFAULT, PAGE_VIEW.
            - origin: A ConversionOrigin enum name. Common values:
              WEBSITE, APP, CALL_FROM_ADS, STORE, YOUTUBE_HOSTED.
            - biddable: bool. True to include this category in the
              campaign's primary `conversions` metric, False to exclude.
        login_customer_id: The Manager Account ID for accessing client
            accounts via a manager. Optional.

    Returns:
        Dictionary with the list of updated resource names and a
        confirmation message.
    """
    if not goals:
        raise ValueError("`goals` must contain at least one entry.")

    client = utils.get_googleads_client(login_customer_id=login_customer_id)
    service = client.get_service("CampaignConversionGoalService")

    operations = []
    for goal in goals:
        category = goal.get("category")
        origin = goal.get("origin")
        if category is None or origin is None or "biddable" not in goal:
            raise ValueError(
                "Each goal must include `category`, `origin`, and `biddable`. "
                f"Received: {goal!r}"
            )

        operation = client.get_type("CampaignConversionGoalOperation")
        update = operation.update
        update.resource_name = service.campaign_conversion_goal_path(
            customer_id, campaign_id, category, origin
        )
        update.biddable = bool(goal["biddable"])

        client.copy_from(
            operation.update_mask, utils.create_field_mask(update)
        )
        operations.append(operation)

    response = service.mutate_campaign_conversion_goals(
        customer_id=customer_id, operations=operations
    )

    updated = [result.resource_name for result in response.results]
    return {
        "updated_resource_names": updated,
        "count": len(updated),
        "message": (
            f"Updated {len(updated)} campaign conversion goal(s) on "
            f"campaign {campaign_id}."
        ),
    }


@mcp.tool()
def update_customer_conversion_goal(
    customer_id: str,
    goals: List[Dict[str, Any]],
    login_customer_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Updates the `biddable` flag on one or more customer-level conversion goals.

    Customer conversion goals are the account-default set of goals that
    new campaigns inherit unless they override with campaign-specific
    goals. Each goal is identified by (category, origin) and only the
    `biddable` field is mutable.

    Args:
        customer_id: The Google Ads customer ID (numbers only, no hyphens).
        goals: List of goal updates. Each item must be a dict with:
            - category: A ConversionActionCategory enum name (e.g. SIGNUP,
              REQUEST_QUOTE, PURCHASE, ENGAGEMENT).
            - origin: A ConversionOrigin enum name (e.g. WEBSITE, APP,
              YOUTUBE_HOSTED).
            - biddable: bool. True to include in the account's default
              `conversions` metric.
        login_customer_id: The Manager Account ID for accessing client
            accounts via a manager. Optional.

    Returns:
        Dictionary with the list of updated resource names and a
        confirmation message.
    """
    if not goals:
        raise ValueError("`goals` must contain at least one entry.")

    client = utils.get_googleads_client(login_customer_id=login_customer_id)
    service = client.get_service("CustomerConversionGoalService")

    operations = []
    for goal in goals:
        category = goal.get("category")
        origin = goal.get("origin")
        if category is None or origin is None or "biddable" not in goal:
            raise ValueError(
                "Each goal must include `category`, `origin`, and `biddable`. "
                f"Received: {goal!r}"
            )

        operation = client.get_type("CustomerConversionGoalOperation")
        update = operation.update
        update.resource_name = service.customer_conversion_goal_path(
            customer_id, category, origin
        )
        update.biddable = bool(goal["biddable"])

        client.copy_from(
            operation.update_mask, utils.create_field_mask(update)
        )
        operations.append(operation)

    response = service.mutate_customer_conversion_goals(
        customer_id=customer_id, operations=operations
    )

    updated = [result.resource_name for result in response.results]
    return {
        "updated_resource_names": updated,
        "count": len(updated),
        "message": (
            f"Updated {len(updated)} customer conversion goal(s) on "
            f"customer {customer_id}."
        ),
    }
