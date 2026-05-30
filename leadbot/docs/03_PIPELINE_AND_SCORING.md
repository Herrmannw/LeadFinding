# LeadBot V1 Pipeline and Scoring Logic

## Pipeline Overview

```text
1. User creates search job
2. Worker generates source queries
3. Worker collects source URLs
4. Worker parses Yelp/Thumbtack pages
5. Worker stores raw_source_records
6. Worker normalizes raw records
7. Worker dedupes into canonical leads
8. Worker checks for website presence
9. Worker scores leads
10. Frontend displays ranked results
```

## Step 1: Create Search Job

Input:

```json
{
  "industry": "HVAC",
  "location": "Houston TX",
  "target_record_count": 500,
  "selected_sources": ["yelp", "thumbtack"]
}
```

Create `search_jobs` row with status `queued`.

`target_record_count` is a best-effort record goal in V1. It is used as the worker's stop condition, but the system may return fewer records when SERP results run out, duplicates are filtered, or provider limits are reached.

## Step 2: Generate Source Queries

For Yelp:

```text
site:yelp.com/biz "{industry}" "{location}"
```

For Thumbtack:

```text
site:thumbtack.com "{industry}" "{location}"
```

Example:

```text
site:yelp.com/biz "HVAC" "Houston TX"
site:thumbtack.com "HVAC" "Houston TX"
```

## Step 3: Collect URLs

Use Google Custom Search, SerpAPI, or another SERP provider.

For each request:
- log to `api_request_logs`
- store query
- store provider
- store status code
- update search job API usage count

Filter results:
- accept URLs matching the selected source domain
- reject category/search pages when possible
- dedupe URLs before fetching

## Step 4: Parse Source Pages

Each source has separate parser code.

Example:

```text
parse_yelp_page(html) → RawSourceRecord model
parse_thumbtack_page(html) → RawSourceRecord model
```

Both parsers return the same normalized shape:

```json
{
  "source_name": "yelp",
  "source_url": "...",
  "business_name": "ABC Heating & Air",
  "phone": "713-555-1234",
  "website_url": null,
  "city": "Houston",
  "state": "TX",
  "category": "HVAC",
  "rating": 4.7,
  "review_count": 34,
  "profile_text": "...",
  "raw_payload": {},
  "parse_confidence": 0.82
}
```

## Step 5: Store Raw Records

Always store raw records before dedupe.

Do not combine in memory and only store the final result.

Reasons:
- debugging
- reprocessing
- parser improvements
- dedupe improvements
- source evidence
- avoiding data loss

## Step 6: Normalize

Normalize fields before dedupe.

Normalize business names:
- lowercase
- remove punctuation
- remove legal suffixes like LLC, Inc, Co
- normalize `&` to `and`
- collapse whitespace

Normalize phones:
- strip punctuation
- strip a leading US country code (`1`) when present
- store as 10-digit US numbers when possible

Normalize domains:
- lowercase
- remove protocol
- remove `www.`
- remove trailing slash

## Step 7: Dedupe

Dedupe hierarchy:

```text
1. Same phone number = same business
2. Same website domain = same business
3. Same exact address = likely same business
4. Similar normalized name + same city = probable duplicate
5. Similar name + same category + same city = possible duplicate
```

Use `rapidfuzz` for fuzzy name matching.

Example threshold:

```text
name similarity >= 90 and same city → merge
name similarity >= 80 and same city/category → needs_review
```

## Step 8: Website Presence Check

This V1 targets businesses that appear alive but do not have their own website.

Do not require website as an alive signal.

Classify website status:

```text
no_website_found
website_found
broken_website
parked_domain
unclear
unknown
```

Signals:
- Source profile includes website link → likely `website_found`
- Source profile has no website → possible no-website signal
- Search for business name + city returns official site → `website_found`
- Search returns only Yelp/Thumbtack/social profiles → possible `no_website_found`
- Found domain is parked/dead → `broken_website` or `parked_domain`

Suggested search checks:

```text
"{business name}" "{city}" "{state}"
"{business name}" "{phone}"
"{business name}" "{category}" "{city}"
```

## Step 9: Scoring

Keep three scores separate:

```text
alive_score
no_website_score
opportunity_score
```

### Alive Score

Goal: does this business appear active enough to contact?

Example rules:

```text
+30 appears on Thumbtack
+25 appears on Yelp
+20 review count above threshold
+15 has phone number
+10 has business description/service list
+10 appears on both Yelp and Thumbtack
+10 has profile photos or other marketplace activity
-40 source/profile says closed/unavailable
-30 no phone and no meaningful activity
```

### No-Website Score

Goal: does this business appear to lack an owned website?

Example rules:

```text
+40 source profile has no website link
+25 search for business name + city does not find obvious official website
+15 only marketplace/social profiles appear
+10 Yelp/Thumbtack appears to be primary web presence
-50 official website found
+20 website is broken/parked
```

Note:
A broken/parked website may be a strong website-opportunity lead even though it is not strictly "no website."

### Opportunity Score

Simple V1 formula:

```text
opportunity_score =
  alive_score * 0.5
+ no_website_score * 0.4
+ category_value * 0.1
```

Or rule-based:

```text
High priority:
alive_score >= 70
AND website_status in ["no_website_found", "broken_website", "parked_domain"]
AND has phone or source contact path
```

## Score Reasons

Every score should include human-readable reasons.

Example:

```json
[
  "Appears on both Yelp and Thumbtack",
  "Yelp profile has 42 reviews",
  "No official website found",
  "Phone number found",
  "Only marketplace profiles appeared in web search"
]
```

## Output Buckets

```text
high_priority
review
low_priority
reject
```

Recommended bucket logic:

```text
high_priority:
  alive_score >= 70 and no_website_score >= 70

review:
  alive_score >= 50 and no_website_score >= 50

low_priority:
  alive_score >= 40 but weak no-website signal

reject:
  likely dead, duplicate, irrelevant, or website clearly found
```

## Important V1 Rule

Do not score before dedupe.

Use:

```text
raw records
→ normalize
→ dedupe into lead
→ synthesize source evidence
→ score lead
```

Reason:
The strongest signal may be "found on both Yelp and Thumbtack", which only exists after combining records.
