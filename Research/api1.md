To integrate the non-real-time NCHL-IPS (Interbank Payment System) for deferred credit payments, you must use the National Payment Interface (NPI), which is the consolidated open API platform provided by Nepal Clearing House Limited (NCHL) 
nchl.com.np
.
Here is a comprehensive list of all available internet resources, categorized by their purpose, to help you with your integration:
1. Official API Documentation (Developer Portal)
The technical API specifications are hosted on the ConnectIPS documentation portal, as NPI acts as the gateway for NCHL-IPS.
NPI Introduction: Explains the architecture, noting that while connectIPS handles real-time transactions, NCHL-IPS supports non-real-time transactions 
doc.connectips.com
. (Link: https://doc.connectips.com/docs/NPI/NPI_Specification/introduction)
API Specifications: Details the exact API endpoints, including how a batch process routes transactions to the creditor bank through the NCHL-IPS system for crediting the beneficiary 
doc.connectips.com
. (Link: https://doc.connectips.com/docs/NPI/NPI_Specification/api_specifications)
Sample Use Cases: Clarifies transaction routing logic, specifying that high-value off-us transactions are processed through NCHL-IPS 
doc.connectips.com
. (Link: https://doc.connectips.com/docs/NPI/NPI_Specification/use_cases)
Remit API Introduction: Covers the open API platform for routing financial transactions for Banks and Financial Institutions (BFIs) 
doc.connectips.com
. (Link: https://doc.connectips.com/docs/Remit/introduction)
Clearing File Specification: Provides details on automated integration and clearing file structures for transaction initiation 
doc.connectips.com
. (Link: https://doc.connectips.com/docs/NPS/Clearing-File-Specification/intro)
2. Official Operational Rulebooks & Guidelines
Before writing code, you must understand the business logic, transaction limits, and compliance rules governing deferred payments.
NCHL-IPS Operating Rule Book (PDF): This is the most critical document for business logic, providing the required rules that control the interbank payment process, including boundaries for direct debit and credit transactions 
nchl.com.np
. (Link: https://nchl.com.np/wp-content/uploads/2023/02/nchl-ips-o-1884711099.pdf)
Rules & Guidelines Portal: The official NCHL page hosting all operating rules, including the NCHL-IPS rulebook and Retail Payment Switch rules 
nchl.com.np
. (Link: https://nchl.com.np/rules-guidelines/)
NRB Rulebook Amendment Notification: A Nepal Rastra Bank (NRB) document detailing specific amendments to the NCHL-IPS Operating Rulebook 
www.nrb.org.np
. (Link: https://www.nrb.org.np/psd/nchl-ips-operating-rulebook-2015...)
3. Official Product & Infrastructure Pages
These pages provide high-level overviews of the systems and the corporate pay features.
NCHL-IPS Product Page: Describes NCHL-IPS as an interbank fund transfer system supporting bulk or one-to-one transactions from participating BFIs 
nchl.com.np
. (Link: https://nchl.com.np/interbank-payment-system-nchl-ips/)
National Payments Interface (NPI) Page: Explains the open API platform concept that provides access to the underlying NCHL-IPS system 
nchl.com.np
. (Link: https://nchl.com.np/national-payments-interface-npi/)
4. Bank-Specific Implementation Guides & Forms
Reviewing how individual banks implement NCHL-IPS can help you understand the required data fields and user flows.
NIC Asia Bank Support Article: A helpful breakdown of what NCHL-IPS is and how it safely transfers funds between different banks 
helpdesk.nicasiabank.com
. (Link: https://helpdesk.nicasiabank.com/support/solutions/articles/35000135865-what-is-interbank-payment-system-nchl-ips-)
NCHL-IPS Fund Transfer Form (PDF): A physical form from Samriddhi Finance that reveals the exact data fields required from a user to initiate an IPS transfer 
sfcl.com.np
. (Link: https://sfcl.com.np/public/uploads/1261486873-IPS%20Form.pdf)
General IPS/RTGS Application Form (PDF): Another example of the required beneficiary and remitter details for fund transfers 
bestfinance.com.np
. (Link: https://bestfinance.com.np/downloadFile?file=IPS-RTGS-Form-Final.pdf)
5. Core System Provider & Industry Context
Understanding the underlying technology and regulatory oversight can be beneficial for enterprise architecture.
Progressoft Implementation News: NCHL-IPS was built and went live using the core banking and payment solutions from Progressoft 
www.progressoft.com
. (Link: https://www.progressoft.com/news/nepal-clearing-house-ltd-started-running-live-the-interbank-payment-system-from-progresssoft)
NRB Payment Systems Oversight Report (PDF): The central bank's report providing macro-level data and regulatory context on the Interbank Payment System in Nepal 
www.nrb.org.np
. (Link: https://www.nrb.org.np/contents/uploads/2025/01/Payment-Oversight-Report-2023-24.pdf)
Academic Paper on connectIPS/NCHL: A journal article discussing the impact of NCHL's systems on transforming banking transactions in Nepal 
Sage
. (Link: https://journals.sagepub.com/doi/abs/10.1177/20438869251335037)
6. Technical Blogs & Community Resources
Tech Blog on NCHL: A developer's technical overview of the Nepal Clearing House Ltd. and its systems 
shyamkumarkc20.com.np
. (Link: https://shyamkumarkc20.com.np/tech/nchl)
⚠️ Crucial Note on API Access
It is important to understand that NCHL APIs (including NPI for NCHL-IPS) are not fully public/open for individual developers.
Access Requirements: To get API keys, sandbox environments, and the full Swagger/OpenAPI specifications, your organization must be a Bank and Financial Institution (BFI), a registered Payment Service Provider (PSP), or a large corporate entity.
Onboarding: You must sign a Non-Disclosure Agreement (NDA) and an integration agreement directly with NCHL.
Official Contact for Integration: You must reach out to NCHL's support or integration team directly to request API documentation and sandbox credentials. You can email them at support@nchl.com.np or call +977-1-5970065 / 4255306 
www.connectips.com
.