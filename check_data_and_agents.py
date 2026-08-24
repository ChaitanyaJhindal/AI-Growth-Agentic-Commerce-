from hybrid_search import ProductHybridSearchEngine
from agent_graph import agent_app

engine = ProductHybridSearchEngine()

print("=" * 60)
print("1. DATABASE AUDIT: WATCHES")
print("=" * 60)
watch_count = engine.collection.count_documents({"article_type": {"$regex": "watch", "$options": "i"}})
print(f"Total Watches in DB: {watch_count}")
sample_watches = list(engine.collection.find({"article_type": {"$regex": "watch", "$options": "i"}}, {"embedding": 0}).limit(3))
for w in sample_watches:
    print(f"  - [{w.get('product_id')}] {w.get('name')} | Article: {w.get('article_type')} | Gender: {w.get('gender')}")

print("\n" + "=" * 60)
print("2. DATABASE AUDIT: WOMEN FOOTWEAR / RUNNING SHOES")
print("=" * 60)
women_footwear = engine.collection.count_documents({"gender": "Women", "master_category": "Footwear"})
women_sports_shoes = engine.collection.count_documents({"gender": "Women", "article_type": {"$regex": "sports", "$options": "i"}})
women_casual_shoes = engine.collection.count_documents({"gender": "Women", "article_type": {"$regex": "shoe", "$options": "i"}})
print(f"Total Women Footwear in DB: {women_footwear}")
print(f"Total Women Sports Shoes in DB: {women_sports_shoes}")
print(f"Total Women Shoes in DB: {women_casual_shoes}")

sample_women_shoes = list(engine.collection.find({"gender": "Women", "master_category": "Footwear"}, {"embedding": 0}).limit(3))
for s in sample_women_shoes:
    print(f"  - [{s.get('product_id')}] {s.get('name')} | Article: {s.get('article_type')} | Gender: {s.get('gender')}")

print("\n" + "=" * 60)
print("3. TESTING AGENT WORKFLOW FOR 'i want to buy watch'")
print("=" * 60)
state_watch = agent_app.invoke({"current_query": "i want to buy watch", "original_query": "i want to buy watch"}, config={"configurable": {"thread_id": "test_watch"}})
print(f"Needs Clarification:   {state_watch.get('needs_clarification')}")
print(f"Clarification Question: {state_watch.get('clarification_question')}")
print(f"Current Query:         '{state_watch.get('current_query')}'")
print(f"Extracted Filters:     {state_watch.get('filters')}")
print(f"Search Results:        {len(state_watch.get('search_results', []))} items")
if state_watch.get('search_results'):
    for p in state_watch.get('search_results')[:3]:
        print(f"  - [{p.get('product_id')}] {p.get('name')} (${p.get('price')}) | {p.get('article_type')}")

print("\n" + "=" * 60)
print("4. TESTING AGENT WORKFLOW FOR 'want to buy running shoes for women'")
print("=" * 60)
state_shoes = agent_app.invoke({"current_query": "want to buy running shoes for women", "original_query": "want to buy running shoes for women"}, config={"configurable": {"thread_id": "test_women_shoes"}})
print(f"Needs Clarification:   {state_shoes.get('needs_clarification')}")
print(f"Clarification Question: {state_shoes.get('clarification_question')}")
print(f"Current Query:         '{state_shoes.get('current_query')}'")
print(f"Extracted Filters:     {state_shoes.get('filters')}")
print(f"Search Results:        {len(state_shoes.get('search_results', []))} items")
if state_shoes.get('search_results'):
    for p in state_shoes.get('search_results')[:3]:
        print(f"  - [{p.get('product_id')}] {p.get('name')} (${p.get('price')}) | {p.get('article_type')}")
