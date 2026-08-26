import json
import random
import urllib.request
from typing import List, Dict, Any, Optional
from src import config

class CampaignAgent:
    """
    Hyper-Personalized Dynamic Campaign & Re-engagement Agent.
    Powered by `openai/gpt-oss-20b` on Groq using dedicated API key.
    
    Generates high-converting, witty, conversational, and culturally-resonant (Hinglish/English)
    promotional messages for WhatsApp, Push Notifications, SMS, and Email based on
    user bag items, categories, and customer name.
    """

    def __init__(self, model: str = "openai/gpt-oss-20b"):
        self.model = model
        self.api_key = config.GROQ_API_KEY_CAMPAIGN or config.GROQ_API_KEY_CONTEXT or config.GROQ_API_KEY
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"

    def generate_message(
        self,
        customer_name: str,
        bag_items: List[Dict[str, Any]],
        channel: str = "whatsapp",
        discount_code: Optional[str] = "AURA10",
        tone: str = "witty_hinglish",
        temperature: float = 1.05
    ) -> Dict[str, Any]:
        """
        Generates a personalized promotional campaign message for a customer with items in their bag.
        
        :param customer_name: Name of the patron (e.g. 'Rahul', 'Priya')
        :param bag_items: List of product dicts in cart/bag
        :param channel: 'whatsapp', 'push', 'sms', or 'email'
        :param discount_code: Optional promotional voucher code
        :param tone: 'witty_hinglish', 'luxury_chic', 'playful_urgency', or 'genz_hype'
        :param temperature: LLM temperature for high creativity & wit
        :return: Dict containing message text, headline, channel, and metadata
        """
        if not customer_name:
            customer_name = "Fashion Lover"

        item_names = [item.get("name", "Piece") for item in bag_items] if bag_items else ["Luxury Fashion Capsule"]
        categories = list(set([item.get("article_type", item.get("sub_category", "Apparel")) for item in bag_items])) if bag_items else ["Fashion"]
        total_price = sum(item.get("price", 45.0) for item in bag_items) if bag_items else 80.0

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "AURA-Fashion/1.0"
        }

        system_instruction = f"""You are AURA's Elite AI Campaign Copywriter & Creative Growth Strategist.
Your superpower is crafting viral, ultra-creative, relatable, and high-converting marketing copy (like top consumer lifestyle apps) that gets opened and converted instantly.

Guidelines:
1. Tone: {tone.replace('_', ' ').title()}. Witty, punchy, conversational, emotional hook, with a natural touch of trendy Hinglish (e.g., 'Bhai/Boss', 'Kya drip hai', 'Cart mein baithe baithe intezaar kar raha hai', 'Look toh fire hai', 'Ab delay kyu?').
2. Always address the customer personally by their name: {customer_name}.
3. Reference the specific items in their bag: {', '.join(item_names[:2])}.
4. Channel Format:
   - whatsapp: 2 to 3 short punchy sentences with relevant emojis, natural storytelling, urgency, and optional voucher code {discount_code}.
   - push: 1 catchy headline (under 8 words) + 1 short body line (under 15 words) with emojis.
   - sms: Crisp under 160 characters message with direct link CTA and code {discount_code}.
   - email: Catchy subject line + 2 engaging paragraphs with styling advice and limited-time offer.
5. Return your response as a valid JSON object with keys:
   - "headline": Short catchy hook / notification title
   - "body": The full promotional message text
   - "call_to_action": Button text (e.g. "Complete Order Now 🔥", "Claim My Look ✨")
   - "suggested_emoji": 1-2 primary emojis"""

        prompt_user = f"""Customer: {customer_name}
Bag Items ({len(bag_items)} items): {', '.join(item_names)}
Categories: {', '.join(categories)}
Total Cart Value: ${total_price:.2f}
Discount Code: {discount_code}
Target Channel: {channel}

Generate an innovative, high-engagement promotional message for this customer now:"""

        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt_user}
            ],
            "temperature": temperature,
            "max_tokens": 300
        }

        # Fallback template in case of offline/network issues
        fallback_headline = f"Hey {customer_name}, your cart is waiting! 🔥"
        fallback_body = (
            f"Bhai {customer_name}, your {item_names[0]} is waiting in your bag! 👟✨ "
            f"Upgrade your aesthetic today with extra off using code *{discount_code}*. "
            f"Don't let someone else snatch your size!"
        )

        try:
            req = urllib.request.Request(self.api_url, data=json.dumps(data).encode("utf-8"), headers=headers)
            with urllib.request.urlopen(req, timeout=4.5) as res:
                res_data = json.loads(res.read().decode("utf-8"))
                raw_text = res_data["choices"][0]["message"]["content"].strip()
                # Clean markdown wrapper if present
                clean_text = raw_text.strip()
                if "```json" in clean_text:
                    clean_text = clean_text.split("```json")[1].split("```")[0].strip()
                elif "```" in clean_text:
                    clean_text = clean_text.split("```")[1].split("```")[0].strip()

                if "{" in clean_text and "}" in clean_text:
                    start = clean_text.index("{")
                    end = clean_text.rindex("}") + 1
                    try:
                        parsed = json.loads(clean_text[start:end])
                        return {
                            "success": True,
                            "customer_name": customer_name,
                            "channel": channel,
                            "headline": parsed.get("headline", fallback_headline),
                            "message": parsed.get("body", fallback_body),
                            "call_to_action": parsed.get("call_to_action", "Claim My Look ✨"),
                            "suggested_emoji": parsed.get("suggested_emoji", "✨🔥"),
                            "model": self.model,
                            "items_referenced": item_names
                        }
                    except Exception:
                        pass
                
                if raw_text:
                    return {
                        "success": True,
                        "customer_name": customer_name,
                        "channel": channel,
                        "headline": fallback_headline,
                        "message": raw_text.replace("```json", "").replace("```", "").strip(),
                        "call_to_action": "Complete Order Now 🔥",
                        "suggested_emoji": "✨🔥",
                        "model": self.model,
                        "items_referenced": item_names
                    }
        except Exception as e:
            print(f"Notice on campaign message generation: {e}")

        return {
            "success": True,
            "customer_name": customer_name,
            "channel": channel,
            "headline": fallback_headline,
            "message": fallback_body,
            "call_to_action": "Complete Order Now 🔥",
            "suggested_emoji": "👟🔥",
            "model": self.model,
            "items_referenced": item_names,
            "fallback_used": True
        }

    def generate_campaign_variations(
        self,
        customer_name: str,
        bag_items: List[Dict[str, Any]],
        count: int = 3,
        discount_code: str = "AURA10"
    ) -> List[Dict[str, Any]]:
        """
        Generates multiple creative variations (e.g. Witty Hinglish, FOMO Urgency, Minimal Luxury)
        for A/B testing across WhatsApp and Push notifications.
        """
        tones = ["witty_hinglish", "playful_urgency", "luxury_chic"]
        channels = ["whatsapp", "push", "sms"]
        variations = []

        for i in range(min(count, len(tones))):
            tone = tones[i]
            channel = channels[i % len(channels)]
            res = self.generate_message(
                customer_name=customer_name,
                bag_items=bag_items,
                channel=channel,
                discount_code=discount_code,
                tone=tone,
                temperature=1.0 + (i * 0.05)
            )
            variations.append(res)

        return variations


# Global singleton instance
_campaign_agent = None

def get_campaign_agent() -> CampaignAgent:
    global _campaign_agent
    if _campaign_agent is None:
        _campaign_agent = CampaignAgent()
    return _campaign_agent
