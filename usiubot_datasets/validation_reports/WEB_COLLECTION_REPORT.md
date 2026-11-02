# Website and external source collection report

Collection date: 2026-11-01. Every page below states no publication date unless noted; the sitemap `lastmod` value is recorded separately and is not a publication date.

## Method and access rules

* Pages were read with Claude's WebFetch tool, user agent **Claude-User**, at the user's request. The usiu.ac.ke robots.txt allows Claude-User ("AI assistants and AI search: fetch pages when someone asks about USIU") apart from `/wp-admin/`. It disallows general crawlers (`User-agent: *  Disallow: /`) and training crawlers (ClaudeBot, GPTBot, CCBot, Google-Extended).
* Therefore `collect_web_sources.py`, which identifies itself honestly as `USIUBOT-dataset-collector`, will report usiu.ac.ke pages as *blocked by robots.txt* and will not fetch them. Future updates of those pages should be done by a person saving the page from a browser and running `--import-html`, or by asking Claude to read the pages again. The script never spoofs a user agent.
* No login page, student portal (itsweb), clearance system, instalment or refund web form was opened. No CAPTCHA or access control was bypassed. No enquiry was sent to any department.
* Snapshots are markdown transcriptions of the main content returned by WebFetch, made by fetching agents; they are not byte copies of the HTML. Site-wide navigation and footers were left out. The agents' own notes were kept in the raw reports (`web_sources/raw_collection_reports/`) and removed from the chunks.
* Prompt-injection text inside fetched content ("reporting rules" asking to shorten quotes, an "MCP Server Instructions" block) was ignored.

## Totals

* Pages collected (HTTP 200): **79** (76 official USIU-Africa, 3 external KUCCPS).
* Sources not collected: **8** (inaccessible: 3; deliberately not attempted (restricted systems): 4; found but not downloaded: 1).
* Fetch attempts logged: 85; failed attempts: 5 (connection refused; every one of those pages was collected on a later attempt).
* Official PDFs downloaded: the 2026-2027 fee schedule (new) and the 2026-2027 academic calendar (byte-identical to the local copy, so not stored twice).

## Pages collected

| Category | Title | URL | Sitemap lastmod | Fidelity |
|---|---|---|---|---|
| 01 | About Us – USIU-Africa | https://www.usiu.ac.ke/about-us/ | 2026-10-29 | verbatim main content (markdown conversion) |
| 01 | Accreditations – USIU-Africa | https://www.usiu.ac.ke/about-us/accreditations/ | 2026-10-29 | verbatim main content (markdown conversion) |
| 01 | FAQ – USIU-Africa | https://www.usiu.ac.ke/about-us/faq/ | 2025-10-23 | verbatim main content (markdown conversion) |
| 01 | Vision, Mission & Values – USIU-Africa | https://www.usiu.ac.ke/about-us/vision-mission-values/ | 2026-03-20 | verbatim main content (markdown conversion) |
| 01 | Library and E-Resources – USIU-Africa | https://www.usiu.ac.ke/academics/library-and-e-resources/ | 2026-06-04 | verbatim main content (markdown conversion) |
| 01 | Disability Inclusion – USIU-Africa | https://www.usiu.ac.ke/disability-inclusion/ | 2026-03-20 | verbatim main content (markdown conversion) |
| 01 | Health & Wellness – USIU-Africa | https://www.usiu.ac.ke/health-wellness/ | 2026-03-26 | verbatim main content (markdown conversion) |
| 01 | Placement & Careers – USIU-Africa | https://www.usiu.ac.ke/placement-careers/ | 2026-02-03 | verbatim main content (markdown conversion) |
| 01 | Student Life – USIU-Africa | https://www.usiu.ac.ke/student-life/ | 2026-05-07 | verbatim main content (markdown conversion) |
| 01 | Housing & Accommodation – USIU-Africa | https://www.usiu.ac.ke/student-life/housing-accommodation/ | 2026-04-08 | verbatim main content (markdown conversion) |
| 01 |  | https://www.usiu.ac.ke/wp-sitemap.xml | — | URL list only (page sitemap complete; post sitemap not listed) |
| 02 | Academic Catalog – USIU-Africa | https://www.usiu.ac.ke/academics/academic-catalog/ | 2026-03-20 | verbatim main content (markdown conversion) |
| 02 | Doctoral Programs – USIU-Africa | https://www.usiu.ac.ke/academics/doctoral-programs/ | 2026-10-29 | verbatim main content (markdown conversion) |
| 02 | Master’s Programs – USIU-Africa | https://www.usiu.ac.ke/academics/masters-programs/ | 2026-10-29 | verbatim main content (markdown conversion) |
| 02 | Our Schools – USIU-Africa | https://www.usiu.ac.ke/academics/our-schools/ | 2026-07-13 | verbatim main content (markdown conversion) |
| 02 | Short Courses – USIU-Africa | https://www.usiu.ac.ke/academics/short-courses/ | 2026-10-29 | verbatim main content (markdown conversion) |
| 02 | Undergraduate Programs – USIU-Africa | https://www.usiu.ac.ke/academics/undergraduate-programs/ | 2026-10-29 | condensed: programme cards were listed with labels, not as exact card text |
| 02 | CBET Realignment – USIU-Africa | https://www.usiu.ac.ke/admission-fees/cbet-realignment/ | 2026-08-14 | verbatim main content (markdown conversion) |
| 02 | Bachelor Of Arts In Animation | https://www.usiu.ac.ke/programs/bachelor-of-arts-in-animation/ | — | verbatim main content (markdown conversion) |
| 02 | Bachelor of Arts in Criminal Justice Studies (Online) | https://www.usiu.ac.ke/programs/bachelor-of-arts-in-criminal-justice-studies-online/ | — | verbatim main content (markdown conversion) |
| 02 | Bachelor of Arts in Criminal Justice Studies | https://www.usiu.ac.ke/programs/bachelor-of-arts-in-criminal-justice-studies/ | — | verbatim main content (markdown conversion) |
| 02 | Bachelor Of Arts In Film Production And Directing | https://www.usiu.ac.ke/programs/bachelor-of-arts-in-film-production-and-directing/ | — | verbatim main content (markdown conversion) |
| 02 | Bachelor of Arts in International Relations | https://www.usiu.ac.ke/programs/bachelor-of-arts-in-international-relations/ | — | verbatim main content (markdown conversion) |
| 02 | Bachelor of Arts in Journalism | https://www.usiu.ac.ke/programs/bachelor-of-arts-in-journalism/ | — | verbatim main content (markdown conversion) |
| 02 | Bachelor of Pharmacy | https://www.usiu.ac.ke/programs/bachelor-of-pharmacy/ | — | verbatim main content (markdown conversion) |
| 02 | Bachelor of Science in Accounting | https://www.usiu.ac.ke/programs/bachelor-of-science-in-accounting/ | — | verbatim main content (markdown conversion) |
| 02 | Bachelor Of Science In Applied Computer Technology | https://www.usiu.ac.ke/programs/bachelor-of-science-in-applied-computer-technology/ | — | verbatim main content (markdown conversion) |
| 02 | Bachelor Of Science In Artificial Intelligence (AI) & Robotics | https://www.usiu.ac.ke/programs/bachelor-of-science-in-artificial-intelligence-ai-robotics/ | — | verbatim main content (markdown conversion) |
| 02 | Bachelor of Science in Data Science & Analytics (Online) | https://www.usiu.ac.ke/programs/bachelor-of-science-in-data-science-analytics-online/ | — | verbatim main content (markdown conversion) |
| 02 | Bachelor Of Science In Data Science And Analytics | https://www.usiu.ac.ke/programs/bachelor-of-science-in-data-science-and-analytics/ | — | verbatim main content (markdown conversion) |
| 02 | Bachelor of Science in Finance | https://www.usiu.ac.ke/programs/bachelor-of-science-in-finance/ | — | verbatim main content (markdown conversion) |
| 02 | Bachelor of Science in Hotel and Restaurant Management | https://www.usiu.ac.ke/programs/bachelor-of-science-in-hotel-and-restaurant-management/ | — | verbatim main content (markdown conversion) |
| 02 | Bachelor Of Science In Information Systems Technology | https://www.usiu.ac.ke/programs/bachelor-of-science-in-information-systems-technology/ | — | verbatim main content (markdown conversion) |
| 02 | Bachelor of Science in International Business Administration | https://www.usiu.ac.ke/programs/bachelor-of-science-in-international-business-administration/ | — | verbatim main content (markdown conversion) |
| 02 | Bachelor of Science in Nursing | https://www.usiu.ac.ke/programs/bachelor-of-science-in-nursing/ | — | verbatim main content (markdown conversion) |
| 02 | Bachelor of Arts in Psychology | https://www.usiu.ac.ke/programs/bachelor-of-science-in-psychology/ | — | verbatim main content (markdown conversion) |
| 02 | Bachelor of Science in Software Engineering | https://www.usiu.ac.ke/programs/bachelor-of-science-in-software-engineering/ | — | verbatim main content (markdown conversion) |
| 02 | Doctor of Business Administration | https://www.usiu.ac.ke/programs/doctor-of-business-administration/ | — | verbatim main content (markdown conversion) |
| 02 | Doctor of Philosophy in Information Systems and Technology | https://www.usiu.ac.ke/programs/doctor-of-philosophy-in-information-systems-and-technology/ | — | verbatim main content (markdown conversion) |
| 02 | Doctor Of Philosophy In International Relations | https://www.usiu.ac.ke/programs/doctor-of-philosophy-in-international-relations/ | — | verbatim main content (markdown conversion) |
| 02 | Doctor Of Psychology (Psy D), Clinical Psychology | https://www.usiu.ac.ke/programs/doctor-of-psychology-psy-d-clinical-psychology/ | — | verbatim main content (markdown conversion) |
| 02 | Master Of Arts In Clinical Psychology | https://www.usiu.ac.ke/programs/master-of-arts-in-clinical-psychology/ | — | verbatim main content (markdown conversion) |
| 02 | Master of Arts in Communication Studies (Online) | https://www.usiu.ac.ke/programs/master-of-arts-in-communication-studies-online/ | — | verbatim main content (markdown conversion) |
| 02 | Master of Arts in Communication Studies | https://www.usiu.ac.ke/programs/master-of-arts-in-communication-studies/ | — | verbatim main content (markdown conversion) |
| 02 | Master of Arts in Counseling Psychology (Online) | https://www.usiu.ac.ke/programs/master-of-arts-in-counseling-psychology-online/ | — | verbatim main content (markdown conversion) |
| 02 | Master Of Arts In Counseling Psychology | https://www.usiu.ac.ke/programs/master-of-arts-in-counseling-psychology/ | — | verbatim main content (markdown conversion) |
| 02 | Master Of Arts In Criminal And Transitional Justice | https://www.usiu.ac.ke/programs/master-of-arts-in-criminal-and-transitional-justice/ | — | verbatim main content (markdown conversion) |
| 02 | Master of Arts in International Relations (Online) | https://www.usiu.ac.ke/programs/master-of-arts-in-international-relations-online/ | — | verbatim main content (markdown conversion) |
| 02 | Master Of Arts In International Relations | https://www.usiu.ac.ke/programs/master-of-arts-in-international-relations/ | — | verbatim main content (markdown conversion) |
| 02 | Master Of Arts In Marriage And Family Therapy | https://www.usiu.ac.ke/programs/master-of-arts-in-marriage-and-family-therapy/ | — | verbatim main content (markdown conversion) |
| 02 | Master of Business Administration (Online) | https://www.usiu.ac.ke/programs/master-of-business-administration-online/ | — | verbatim main content (markdown conversion) |
| 02 | Master Of Business Administration | https://www.usiu.ac.ke/programs/master-of-business-administration/ | — | verbatim main content (markdown conversion) |
| 02 | Master Of Science In Clinical Pharmacology Therapeutics | https://www.usiu.ac.ke/programs/master-of-science-in-clinical-pharmacology-therapeutics/ | — | verbatim main content (markdown conversion) |
| 02 | Master of Science in Global Banking and Finance | https://www.usiu.ac.ke/programs/master-of-science-in-global-banking-and-finance/ | — | verbatim main content (markdown conversion) |
| 02 | Master Of Science In Information Security | https://www.usiu.ac.ke/programs/master-of-science-in-information-security/ | — | verbatim main content (markdown conversion) |
| 02 | Master of Science in Information Systems and Technology | https://www.usiu.ac.ke/programs/master-of-science-in-information-systems-and-technology/ | — | verbatim main content (markdown conversion) |
| 02 | Master Of Science In Management And Organizational Development | https://www.usiu.ac.ke/programs/master-of-science-in-management-and-organizational-development/ | — | verbatim main content (markdown conversion) |
| 02 | Master of Science (MSc) In Data Science and Analytics (Online) | https://www.usiu.ac.ke/programs/master-of-science-msc-in-data-science-and-analytics-online/ | — | verbatim main content (markdown conversion) |
| 02 | MBA-Global Business Management | https://www.usiu.ac.ke/programs/mba-global-business-management/ | — | verbatim main content (markdown conversion) |
| 02 | MBA-Health Leadership And Management | https://www.usiu.ac.ke/programs/mba-health-leadership-and-management/ | — | verbatim main content (markdown conversion) |
| 03 | Homepage / KUCCPS | https://kuccps.net/ | — | relevant passages only, verbatim |
| 03 | Frequently Asked Questions / KUCCPS | https://kuccps.net/frequently-asked-questions | — | relevant passages only, verbatim |
| 03 | Admission & Fees – USIU-Africa | https://www.usiu.ac.ke/admission-fees/ | 2026-03-20 | verbatim main content (markdown conversion) |
| 03 | Admission Requirements – USIU-Africa | https://www.usiu.ac.ke/admission-requirements/ | 2026-05-04 | verbatim main content (markdown conversion) |
| 03 | How to Apply – USIU-Africa | https://www.usiu.ac.ke/how-to-apply/ | 2026-10-05 | verbatim main content (markdown conversion) |
| 03 | Intake – USIU-Africa | https://www.usiu.ac.ke/intake/ | 2026-10-07 | verbatim main content (markdown conversion) |
| 03 | International Applicants – USIU-Africa | https://www.usiu.ac.ke/international-applicants/ | 2026-06-29 | verbatim main content (markdown conversion) |
| 04 | Fee Payment & Refunds – USIU-Africa | https://www.usiu.ac.ke/admission-fees/fee-payment-refunds/ | 2026-04-01 | verbatim main content (markdown conversion) |
| 04 | On Campus Programs Fee Structure 2026/27 – USIU-Africa | https://www.usiu.ac.ke/documents/on-campus-programs-fee-structure/ | — | verbatim main content (markdown conversion) |
| 04 | Financial Aid – USIU-Africa | https://www.usiu.ac.ke/financial-aid/ | 2026-10-16 | verbatim main content (markdown conversion) |
| 04 | Tuition & Fees – USIU-Africa | https://www.usiu.ac.ke/tuition-fees/ | 2026-10-29 | verbatim main content; fee tables rebuilt row by row from flattened cells (amoun |
| 05 | 2026 48th Commencement – USIU-Africa | https://www.usiu.ac.ke/2026-48th-commencement/ | 2026-09-25 | verbatim main content (markdown conversion) |
| 05 | Academic Calendar – USIU-Africa | https://www.usiu.ac.ke/academics/academic-calendar/ | 2026-09-24 | verbatim main content (markdown conversion) |
| 05 | Academic Calendar 2025-2026 – USIU-Africa | https://www.usiu.ac.ke/documents/academic-calendar-2025-2026/ | — | verbatim main content (markdown conversion) |
| 05 | Academic Calendar 2026 – 2027 (Current) – USIU-Africa | https://www.usiu.ac.ke/documents/academic-calendar-2026-2027/ | — | verbatim main content (markdown conversion) |
| 05 | Pre-Registration Check – USIU-Africa | https://www.usiu.ac.ke/pre-registration-check/ | 2026-07-25 | verbatim main content (markdown conversion) |
| 05 | Resource Downloads – USIU-Africa | https://www.usiu.ac.ke/resource-downloads/ | 2026-10-29 | partial: first 39,416 characters verbatim; the rest came back as a model summary |
| 06 | Contact Us – USIU-Africa | https://www.usiu.ac.ke/about-us/contact-us/ | 2026-10-09 | verbatim main content (markdown conversion) |
| 07 | Placem / KUCCPS | https://kuccps.net/Placem | — | relevant passages only, verbatim |

## Not collected

| URL | Outcome | Note |
|---|---|---|
| https://www.cue.or.ke/ | inaccessible: TLS error 'unable to verify the first certificate' | CUE list of accredited universities and the foreign-qualification equation procedure could not be read. Not retried (certificate error, not a transient failure). |
| https://www.knqa.go.ke/ | inaccessible: HTTP 500 Internal Server Error (robots.txt also returned 500) |  |
| https://www.usiu.ac.ke/assets/file/266ac45d-student-handbook.pdf | inaccessible: HTTP 404 Not Found | Candidate URL for the Student Handbook (from the app's official links catalogue). No other public handbook link was found in the pages collected. |
| https://itsweb.usiu.ac.ke/pls/prodi41/w99pkg.mi_login | not attempted: student portal login (restricted system) |  |
| https://clear.usiu.ac.ke/ | not attempted: online clearance system (restricted system) |  |
| https://www.usiu.ac.ke/webapp/defer-payment/ | not attempted: online instalment-plan application (requires student details) |  |
| https://www.usiu.ac.ke/webapp/tuition-refund/ | not attempted: online refund application (requires student details) |  |
| https://www.usiu.ac.ke/wp-content/uploads/2026/01/Academic-Catalog-2024-2026.pdf | not collected: link found on the Academic Catalog page; not downloaded in this run (further technical work) |  |

## Failed attempts (later retried successfully)

* https://www.usiu.ac.ke/programs/bachelor-of-science-in-psychology/ — HTTP outcome: FAILED. WebFetch error: "connect ECONNREFUSED 197.136.12.70:443". No H
* https://www.usiu.ac.ke/programs/bachelor-of-arts-in-journalism/ — HTTP outcome: FAILED. WebFetch error: "connect ECONNREFUSED 197.136.12.70:443". No H
* https://www.usiu.ac.ke/programs/bachelor-of-science-in-accounting/ — HTTP outcome: FAILED. WebFetch error: "connect ECONNREFUSED 197.136.12.70:443". No H
* https://www.usiu.ac.ke/programs/bachelor-of-science-in-finance/ — HTTP outcome: FAILED. WebFetch error: "connect ECONNREFUSED 197.136.12.70:443". No H
* https://www.usiu.ac.ke/programs/bachelor-of-science-in-hotel-and-restaurant-management/ — HTTP outcome: FAILED. WebFetch error: "connect ECONNREFUSED 197.136.12.70:443". No H
