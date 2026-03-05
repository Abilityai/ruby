#!/usr/bin/env python3
"""
Create comprehensive influencer database by merging research data with Twitter API data
"""

import json
from pathlib import Path

# Category mappings (from research)
INFLUENCER_CATEGORIES = {
    # AI Researchers & Thought Leaders
    "ylecun": {
        "category": "ai_researchers",
        "priority": "high",
        "pillars": ["Technical Deep Dives", "Industry Hot Takes"],
        "why_monitor": "Leading AI researcher, candid contrarian takes on AI limitations",
        "role": "VP & Chief AI Scientist at Meta"
    },
    "demishassabis": {
        "category": "ai_researchers",
        "priority": "high",
        "pillars": ["Technical Deep Dives", "Industry Hot Takes"],
        "why_monitor": "DeepMind CEO, shares major AI breakthroughs",
        "role": "CEO of Google DeepMind"
    },
    "sama": {
        "category": "ai_researchers",
        "priority": "high",
        "pillars": ["Founder Lessons", "Industry Hot Takes"],
        "why_monitor": "OpenAI CEO, high-level AI landscape and implications",
        "role": "CEO of OpenAI"
    },
    "karpathy": {
        "category": "ai_researchers",
        "priority": "high",
        "pillars": ["Technical Deep Dives", "Agent Design Patterns"],
        "why_monitor": "Breaks down complex AI concepts, practical educator",
        "role": "Founding member OpenAI, former Director of AI at Tesla"
    },
    "drfeifei": {
        "category": "ai_researchers",
        "priority": "high",
        "pillars": ["AI Adoption Psychology", "Industry Hot Takes"],
        "why_monitor": "Prominent voice on ethical and societal AI impacts",
        "role": "Professor at Stanford, Co-Director Stanford HAI"
    },
    # AI Agent Framework Creators
    "hwchase17": {
        "category": "framework_creators",
        "priority": "high",
        "pillars": ["Agent Design Patterns", "Technical Deep Dives"],
        "why_monitor": "LangChain CEO, essential for agent builders",
        "role": "Co-founder and CEO of LangChain"
    },
    "joao_g_s": {
        "category": "framework_creators",
        "priority": "medium",
        "pillars": ["Agent Design Patterns", "Technical Deep Dives"],
        "why_monitor": "CrewAI creator, rising voice in multi-agent systems",
        "role": "Creator of CrewAI"
    },
    "joereis": {
        "category": "framework_creators",
        "priority": "medium",
        "pillars": ["Technical Deep Dives", "Founder Lessons"],
        "why_monitor": "Data-centric AI advocate, data engineering for AI",
        "role": "Co-founder of Galileo"
    },
    # AI Startup Founders
    "alexandr_wang": {
        "category": "ai_founders",
        "priority": "high",
        "pillars": ["Founder Lessons", "Industry Hot Takes"],
        "why_monitor": "Scale AI CEO, insights into AI data infrastructure",
        "role": "Founder and CEO of Scale AI"
    },
    "aravsrinivas": {
        "category": "ai_founders",
        "priority": "high",
        "pillars": ["Founder Lessons", "Industry Hot Takes"],
        "why_monitor": "Perplexity CEO, challenging traditional search with AI",
        "role": "Co-founder and CEO of Perplexity AI"
    },
    "ClementDelangue": {
        "category": "ai_founders",
        "priority": "high",
        "pillars": ["Founder Lessons", "Industry Hot Takes"],
        "why_monitor": "Hugging Face CEO, key figure in open-source AI",
        "role": "Co-founder and CEO of Hugging Face"
    },
    "aidangomez": {
        "category": "ai_founders",
        "priority": "medium",
        "pillars": ["Founder Lessons", "Technical Deep Dives"],
        "why_monitor": "Cohere CEO, transformer paper co-author",
        "role": "Co-founder and CEO of Cohere"
    },
    "bindureddy": {
        "category": "ai_founders",
        "priority": "medium",
        "pillars": ["Founder Lessons", "Technical Deep Dives"],
        "why_monitor": "Abacus.AI CEO, practical enterprise AI deployment",
        "role": "Co-founder and CEO of Abacus.AI"
    },
    # AI Journalists
    "karenhao": {
        "category": "ai_journalists",
        "priority": "medium",
        "pillars": ["AI Adoption Psychology", "Industry Hot Takes"],
        "why_monitor": "Deep dives into human side of AI, societal impacts",
        "role": "AI journalist, MIT Tech Review, WSJ"
    },
    "sharon": {
        "category": "ai_journalists",
        "priority": "low",
        "pillars": ["Industry Hot Takes", "Founder Lessons"],
        "why_monitor": "Business of AI analysis, corporate strategies",
        "role": "Senior writer at Fortune covering AI"
    },
    "rowancheung": {
        "category": "ai_journalists",
        "priority": "high",
        "pillars": ["Industry Hot Takes"],
        "why_monitor": "High-signal AI news feed, The Rundown founder",
        "role": "Founder of The Rundown AI newsletter"
    },
    # Enterprise AI Leaders
    "alliekmiller": {
        "category": "enterprise_leaders",
        "priority": "medium",
        "pillars": ["AI Adoption Psychology", "Founder Lessons"],
        "why_monitor": "Practical business AI application advice",
        "role": "AI entrepreneur, former AWS Global Head of ML"
    },
    "cassiekozyrkov": {
        "category": "enterprise_leaders",
        "priority": "high",
        "pillars": ["AI Adoption Psychology", "Technical Deep Dives"],
        "why_monitor": "Demystifies complex AI/data concepts for broad audience",
        "role": "Chief Decision Scientist at Google"
    },
    "tessalau": {
        "category": "enterprise_leaders",
        "priority": "low",
        "pillars": ["Founder Lessons", "AI Adoption Psychology"],
        "why_monitor": "AI/robotics in traditional industries, adoption challenges",
        "role": "Founder & CEO of Dusty Robotics"
    },
    # VCs & Investors
    "eladgil": {
        "category": "vcs",
        "priority": "high",
        "pillars": ["Founder Lessons", "Industry Hot Takes"],
        "why_monitor": "Must-read for startup landscape insights",
        "role": "Entrepreneur and investor, AI focus"
    },
    "sarahguo": {
        "category": "vcs",
        "priority": "medium",
        "pillars": ["Founder Lessons", "Industry Hot Takes"],
        "why_monitor": "Sharp AI market analysis, advice for AI founders",
        "role": "Founder of Conviction VC"
    },
    "a16z": {
        "category": "vcs",
        "priority": "high",
        "pillars": ["Industry Hot Takes", "Founder Lessons"],
        "why_monitor": "Curated insights from top VC firm",
        "role": "Andreessen Horowitz official account"
    },
    # Developer Advocates & Educators
    "AndrewYNg": {
        "category": "educators",
        "priority": "high",
        "pillars": ["Technical Deep Dives", "AI Adoption Psychology"],
        "why_monitor": "Leading AI educator, makes AI accessible globally",
        "role": "Co-founder of Coursera, founder of DeepLearning.AI"
    },
    "rasbt": {
        "category": "educators",
        "priority": "medium",
        "pillars": ["Technical Deep Dives"],
        "why_monitor": "Go-to resource for ML algorithm understanding",
        "role": "ML researcher and educator"
    },
    "huggingface": {
        "category": "educators",
        "priority": "high",
        "pillars": ["Technical Deep Dives", "Agent Design Patterns"],
        "why_monitor": "Central hub for new models, datasets, tutorials",
        "role": "Official Hugging Face account"
    },
    # Rising Stars
    "michi_sato": {
        "category": "rising_stars",
        "priority": "low",
        "pillars": ["AI Adoption Psychology", "Industry Hot Takes"],
        "why_monitor": "Fresh perspective on AI and humanity intersection",
        "role": "AI researcher and artist"
    },
    "chipro": {
        "category": "rising_stars",
        "priority": "medium",
        "pillars": ["Technical Deep Dives", "Agent Design Patterns"],
        "why_monitor": "MLOps expertise, practical ML engineering",
        "role": "Co-founder of Claypot AI, MLOps educator"
    },
    "mathemagic1an": {
        "category": "rising_stars",
        "priority": "medium",
        "pillars": ["Technical Deep Dives"],
        "why_monitor": "Hidden gem for understanding technical AI breakthroughs",
        "role": "Anonymous technical AI explainer"
    },
    # Additional High-Priority
    "AnthropicAI": {
        "category": "ai_companies",
        "priority": "high",
        "pillars": ["Industry Hot Takes", "Technical Deep Dives"],
        "why_monitor": "Official Anthropic account, Claude updates",
        "role": "Official Anthropic account"
    },
    "DarioAmodei": {
        "category": "ai_researchers",
        "priority": "high",
        "pillars": ["Industry Hot Takes", "Technical Deep Dives"],
        "why_monitor": "Anthropic CEO, AI safety focus",
        "role": "CEO of Anthropic"
    },
    "jared_kaplan": {
        "category": "ai_researchers",
        "priority": "medium",
        "pillars": ["Technical Deep Dives"],
        "why_monitor": "Anthropic co-founder, scaling laws research",
        "role": "Co-founder, Anthropic"
    },
    "satyanadella": {
        "category": "enterprise_leaders",
        "priority": "high",
        "pillars": ["Industry Hot Takes", "AI Adoption Psychology"],
        "why_monitor": "Microsoft CEO, enterprise AI strategy",
        "role": "CEO of Microsoft"
    },
    "ericboyd": {
        "category": "enterprise_leaders",
        "priority": "low",
        "pillars": ["Technical Deep Dives"],
        "why_monitor": "Microsoft AI Platform leadership",
        "role": "CVP Microsoft AI Platform"
    },
    "JeffDean": {
        "category": "ai_researchers",
        "priority": "high",
        "pillars": ["Technical Deep Dives"],
        "why_monitor": "Google AI leadership, technical insights",
        "role": "Chief Scientist, Google DeepMind"
    },
    "sundarpichai": {
        "category": "enterprise_leaders",
        "priority": "medium",
        "pillars": ["Industry Hot Takes"],
        "why_monitor": "Google CEO, AI vision",
        "role": "CEO of Google/Alphabet"
    },
    "gdb": {
        "category": "ai_researchers",
        "priority": "high",
        "pillars": ["Technical Deep Dives", "Founder Lessons"],
        "why_monitor": "OpenAI President, technical and strategic insights",
        "role": "President of OpenAI"
    },
    "ilyasut": {
        "category": "ai_researchers",
        "priority": "medium",
        "pillars": ["Technical Deep Dives"],
        "why_monitor": "AI safety researcher, former OpenAI",
        "role": "Former Chief Scientist at OpenAI"
    },
    "jackclark": {
        "category": "ai_researchers",
        "priority": "medium",
        "pillars": ["Industry Hot Takes", "AI Adoption Psychology"],
        "why_monitor": "Anthropic co-founder, AI policy focus",
        "role": "Co-founder, Anthropic"
    },
    # Additional thought leaders
    "pmarca": {
        "category": "vcs",
        "priority": "high",
        "pillars": ["Founder Lessons", "Industry Hot Takes"],
        "why_monitor": "a16z co-founder, tech trends and philosophy",
        "role": "Co-founder of Andreessen Horowitz"
    },
    "shreyas": {
        "category": "educators",
        "priority": "medium",
        "pillars": ["Founder Lessons"],
        "why_monitor": "Product management insights, startup lessons",
        "role": "Product advisor, former PM at Stripe/Twitter"
    },
    "naval": {
        "category": "vcs",
        "priority": "high",
        "pillars": ["Founder Lessons", "Industry Hot Takes"],
        "why_monitor": "AngelList founder, startup philosophy",
        "role": "Founder of AngelList"
    },
    "paulg": {
        "category": "vcs",
        "priority": "high",
        "pillars": ["Founder Lessons"],
        "why_monitor": "Y Combinator founder, startup wisdom",
        "role": "Founder of Y Combinator"
    },
    "lennysan": {
        "category": "educators",
        "priority": "low",
        "pillars": ["Founder Lessons"],
        "why_monitor": "Product and growth insights",
        "role": "Creator of Lenny's Newsletter"
    },
    "emollick": {
        "category": "educators",
        "priority": "high",
        "pillars": ["AI Adoption Psychology", "Industry Hot Takes"],
        "why_monitor": "AI in education and work, practical use cases",
        "role": "Professor at Wharton, AI adoption expert"
    }
}

def create_database():
    """Merge category data with Twitter API data"""

    # Load Twitter API data
    api_data_path = Path(".claude/memory/influencer_twitter_data.json")
    with open(api_data_path) as f:
        api_data = json.load(f)

    # Create lookup by username
    api_lookup = {user["username"]: user for user in api_data}

    # Build comprehensive database
    database = {
        "version": "1.0",
        "last_updated": "2025-01-24",
        "total_influencers": 0,
        "categories": {},
        "influencers": []
    }

    # Process each influencer
    for username, meta in INFLUENCER_CATEGORIES.items():
        # Get API data
        api_info = api_lookup.get(username, {})

        if not api_info:
            print(f"Warning: No API data for @{username}")
            continue

        # Build comprehensive record
        influencer = {
            "username": username,
            "user_id": api_info.get("id"),
            "display_name": api_info.get("name"),
            "bio": api_info.get("description", ""),
            "location": api_info.get("location", ""),
            "verified": api_info.get("verified", False),
            "followers_count": api_info.get("public_metrics", {}).get("followers_count", 0),
            "following_count": api_info.get("public_metrics", {}).get("following_count", 0),
            "tweet_count": api_info.get("public_metrics", {}).get("tweet_count", 0),
            "profile_image_url": api_info.get("profile_image_url", ""),
            "category": meta["category"],
            "priority": meta["priority"],
            "pillars": meta["pillars"],
            "why_monitor": meta["why_monitor"],
            "role": meta["role"],
            "account_created": api_info.get("created_at", "")
        }

        database["influencers"].append(influencer)

    # Sort by priority (high > medium > low) then by followers
    priority_order = {"high": 0, "medium": 1, "low": 2}
    database["influencers"].sort(
        key=lambda x: (priority_order[x["priority"]], -x["followers_count"])
    )

    # Build category summary
    categories = {}
    for inf in database["influencers"]:
        cat = inf["category"]
        if cat not in categories:
            categories[cat] = {
                "count": 0,
                "total_followers": 0,
                "accounts": []
            }
        categories[cat]["count"] += 1
        categories[cat]["total_followers"] += inf["followers_count"]
        categories[cat]["accounts"].append(inf["username"])

    database["categories"] = categories
    database["total_influencers"] = len(database["influencers"])

    # Save
    output_path = Path(".claude/memory/ai_tech_influencers_database.json")
    with open(output_path, "w") as f:
        json.dump(database, f, indent=2)

    print(f"✓ Created database: {output_path}")
    print(f"✓ Total influencers: {database['total_influencers']}")
    print(f"\nCategory breakdown:")
    for cat, info in sorted(categories.items(), key=lambda x: -x[1]["total_followers"]):
        print(f"  {cat}: {info['count']} accounts, {info['total_followers']:,} total followers")

    return database

if __name__ == "__main__":
    create_database()
