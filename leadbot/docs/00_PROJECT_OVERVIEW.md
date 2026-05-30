# LeadBot V1 Project Overview

## Product Goal

Build a simple internal web app that finds local service businesses from Yelp and Thumbtack, combines duplicate records, and identifies companies that appear active but do not have their own website.

This is not a full CRM and will not integrate with HubSpot in V1.

## V1 Target User

A small marketing/web-design agency operator who wants to find local businesses that may need a basic website or web presence package.

## V1 User Flow

1. User opens a simple web frontend.
2. User enters:
   - industry/search term, e.g. `HVAC`
   - location, e.g. `TX`, `Houston TX`, `Dallas TX`
   - record goal / best-effort target, e.g. `500`
   - selected sources: Yelp, Thumbtack
3. App creates a search job.
4. Backend collects search result URLs using Google/SERP search operators.
5. Backend scrapes/parses Yelp and Thumbtack pages.
6. Raw records are stored.
7. Records are normalized and deduped into canonical leads.
8. A scoring process rates each lead for:
   - whether the business appears alive/active
   - whether the business appears to lack an official website
   - whether it is a viable outreach opportunity
9. Frontend displays a ranked table of leads.

## V1 Scope

Included:

- Search jobs
- Yelp source collection
- Thumbtack source collection
- Raw source record storage
- Normalization
- Dedupe/synthesis
- Alive scoring
- No-website scoring
- Opportunity scoring
- Simple dashboard/table
- CSV export if easy
- API usage logging

Excluded:

- HubSpot integration
- Automated outreach
- Email sending
- Google Maps scraping
- Advanced AI agents
- Full CRM features
- Raw HTML warehousing
- Perfect dedupe
- More than Yelp and Thumbtack

## Core Product Definition

LeadBot V1 is:

> A tool that searches Yelp and Thumbtack for local service businesses, merges duplicate listings, identifies companies that appear active but lack an official website, and ranks them as outreach opportunities.

## Target Lead Type

The best V1 lead is not necessarily a business with a bad website. The target is:

> Alive local business + marketplace presence + no obvious owned website.

Examples:

- HVAC contractor active on Yelp but no official website found
- Thumbtack service provider with reviews/hires but no site
- Business appears on both Yelp and Thumbtack but only has marketplace/social pages

## Success Criteria

The first useful milestone:

> Generate 100 mostly-real HVAC leads in one Texas city, dedupe them, and rank the top 20 by likely no-website opportunity.

The tool is successful if a human can review the top-ranked results and quickly see:
- business name
- source links
- city/state
- phone/contact path if found
- website status
- why the lead was scored highly
