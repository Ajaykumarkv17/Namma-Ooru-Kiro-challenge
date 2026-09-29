# Requirements Document

## Introduction
Namma Ooru is a Tamil Nadu travel discovery and planning application for travelers who need
reliable destination information, structured recommendations, and grounded AI assistance. The
application must support independent browsing as well as a demonstrable AI workflow: search for a
destination, inspect a place, ask a grounded question, generate a multi-day itinerary, and modify
that itinerary conversationally. Destination facts are source-attributed and unknown factual fields
remain unavailable rather than being fabricated.

## Glossary
- **Namma Ooru**: The web application defined by this specification.
- **Destination**: A catalogued Tamil Nadu place represented by a unique destination identifier.
- **Destination Catalog**: The validated collection of Destination records.
- **Destination Repository**: The backend abstraction that retrieves Destination records.
- **Travel Query**: A natural-language request for destinations or a trip plan.
- **Search Filter**: A selected city, district, category, tag, or travel attribute used to limit results.
- **Itinerary**: An ordered set of one or more numbered day plans.
- **Itinerary Activity**: A timed visit to one Destination in an Itinerary.
- **Knowledge Base**: The Amazon Bedrock Knowledge Base populated from validated destination documents.
- **Grounded Response**: AI-generated text supported only by retrieved Knowledge Base content.
- **Review**: A user-authored rating and optional text associated with one Destination.
- **AI Provider**: The interface implemented by the Amazon Bedrock provider and the local mock provider.

## Requirements

### Requirement 1: Discovery Home and Browsing
**User Story:** As a traveler, I want a visually rich discovery home page, so that I can explore Tamil Nadu without first using AI.
#### Acceptance Criteria
1. WHEN a traveler opens the Namma Ooru home page, THE Namma Ooru application SHALL display a hero section, a destination search control, and an Explore Tamil Nadu call to action.
2. WHEN the Destination Catalog is available, THE Namma Ooru application SHALL display popular destinations, popular cities, categories, hidden gems, and recommended destinations.
3. WHILE home-page destination data is loading, THE Namma Ooru application SHALL display skeleton content for each data-driven section.
4. IF a home-page section has no matching Destination records, THEN THE Namma Ooru application SHALL display an empty state with a discovery action.
5. WHEN a traveler selects a Destination or city card, THE Namma Ooru application SHALL navigate to the corresponding detail page without requiring an AI request.

### Requirement 2: City and Destination Details
**User Story:** As a traveler, I want detailed city and destination pages, so that I can decide what to visit.
#### Acceptance Criteria
1. WHEN a traveler opens a city page, THE Namma Ooru application SHALL display the city overview and grouped Destination sections for popular places, temples, heritage, food, nature or nearby attractions, and hidden gems when matching records exist.
2. WHEN a traveler opens a Destination page, THE Namma Ooru application SHALL display the Destination description, category, images, ratings, reviews, nearby places, best time to visit, recommended duration, and source link when those fields are available.
3. WHERE a Destination field has a null value, THE Namma Ooru application SHALL display “Information unavailable” instead of a factual replacement.
4. WHEN a traveler selects a nearby Destination, THE Namma Ooru application SHALL navigate to that Destination page.

### Requirement 3: Destination Catalog and Data Quality
**User Story:** As a maintainer, I want a structured and validated Destination Catalog, so that destinations can be added without changing application components.
#### Acceptance Criteria
1. THE Destination Repository SHALL store Destination records separately from frontend components.
2. THE Destination Repository SHALL represent each Destination with a unique id, name, alternate names, city, district, region, category, description, coordinates when verified, source references, tags, nearby-place identifiers, discovery flags, and popularity metadata.
3. THE Destination Repository SHALL accept the categories Temples, Heritage, Beaches, Hills, Waterfalls, Nature, Wildlife, Food, Culture, Adventure, Photography, and Hidden Gems.
4. WHEN the data validator processes a Destination record, THE data validator SHALL reject a record with a duplicate identifier, an invalid district, an invalid category, invalid coordinates, an empty description, or no source reference.
5. WHEN source records conflict about a Destination fact, THE data validator SHALL emit a human-review flag and preserve the authoritative-source preference in source notes.
6. WHERE a factual value is not verified by a source, THE Destination Repository SHALL persist a null value for that field.

### Requirement 4: Natural-Language Search and Filtering
**User Story:** As a traveler, I want to search in natural language and refine results, so that I can find relevant destinations without knowing exact names.
#### Acceptance Criteria
1. WHEN a traveler submits a Travel Query, THE AI Provider SHALL return structured search intent containing any recognized location, duration, category, interests, travel style, budget, and group context.
2. WHEN the Namma Ooru application completes a Travel Query, THE Namma Ooru application SHALL display structured Destination results.
3. WHEN an AI Provider is unavailable, THE Namma Ooru application SHALL perform keyword and tag matching and identify the fallback to the traveler.
4. WHEN one or more Search Filters are active, THE Destination Repository SHALL return only Destination records that satisfy every active Search Filter.
5. WHEN a traveler removes one Search Filter, THE Destination Repository SHALL preserve the effect of every remaining active Search Filter.

### Requirement 5: Grounded Bedrock Chatbot
**User Story:** As a traveler, I want a chatbot grounded in Namma Ooru travel data, so that answers do not invent travel facts.
#### Acceptance Criteria
1. THE Knowledge Base SHALL use validated destination documents stored in Amazon S3 as its source and Amazon S3 Vectors as its vector store.
2. WHEN a traveler submits a chatbot question, THE AI Provider SHALL retrieve relevant Knowledge Base content before generating a Grounded Response.
3. WHEN the AI Provider returns a Grounded Response, THE backend API SHALL return retrieved source references separately from generated response text.
4. IF the Knowledge Base contains no relevant content, THEN THE AI Provider SHALL return an unavailable-information response instead of an unsupported factual answer.
5. WHEN the application displays generated chatbot text, THE Namma Ooru application SHALL label the text as AI-generated and provide source Destination links when the backend API returns them.

### Requirement 6: Multi-Day Itinerary Generation
**User Story:** As a traveler, I want a multi-day itinerary based on my travel preferences, so that I can plan a coherent trip.
#### Acceptance Criteria
1. WHEN a traveler submits a destination, day count, budget, travel style, interests, starting point, and optional constraints, THE itinerary service SHALL generate an Itinerary containing the requested number of day plans.
2. WHEN the itinerary service creates an Itinerary Activity, THE itinerary service SHALL reference a Destination in the Destination Catalog and assign a positive visit duration.
3. WHEN the itinerary service creates a day plan, THE itinerary service SHALL order non-overlapping Itinerary Activities by start time.
4. WHEN the itinerary service selects activities, THE itinerary service SHALL consider destination coordinates, known opening hours, recommended duration, traveler interests, travel style, and budget constraints.
5. IF the traveler sets `allow_repeats` to false, THEN THE itinerary service SHALL include each Destination no more than once in an Itinerary.
6. WHEN the Namma Ooru application displays an Itinerary Activity, THE Namma Ooru application SHALL display the time, place, approximate duration, visit rationale, travel context, and a food or break suggestion.

### Requirement 7: Conversational Itinerary Editing
**User Story:** As a traveler, I want to modify an existing itinerary conversationally, so that I can refine it without rebuilding the trip.
#### Acceptance Criteria
1. WHEN a traveler submits an itinerary-edit request, THE AI Provider SHALL translate the request into a structured add, remove, replace, reorder, or constraint operation.
2. WHEN the itinerary service applies a structured itinerary operation, THE itinerary service SHALL preserve every unaffected Itinerary Activity.
3. WHEN the itinerary service applies a structured itinerary operation, THE itinerary service SHALL preserve valid Destination references, positive durations, and non-overlapping time ordering.
4. IF an itinerary-edit request has no valid result, THEN THE itinerary service SHALL return an explanation and the unchanged Itinerary.

### Requirement 8: Personalized and Themed Discovery
**User Story:** As a traveler, I want recommendations matched to my interests, so that I can discover destinations beyond common tourist routes.
#### Acceptance Criteria
1. WHEN a traveler selects one or more interests, THE recommendation service SHALL return Destination records whose categories or tags match the selected interests.
2. WHEN a traveler selects Surprise Me, THE recommendation service SHALL return one Destination record with a matching rationale, category, suggested duration, and short description.
3. WHEN a traveler selects a Spiritual Journey, Hill Escape, Coastal Escape, Food Trail, Heritage Journey, Nature Escape, Photography Trip, or Hidden Gems journey, THE recommendation service SHALL return matching Destination records.
4. THE recommendation service SHALL return only Destination records present in the Destination Catalog.

### Requirement 9: Interactive Tamil Nadu Map
**User Story:** As a traveler, I want to discover destinations on a map, so that I can understand their location and navigate to details.
#### Acceptance Criteria
1. WHEN a traveler opens the map, THE map service SHALL display a marker for every matching Destination record with verified coordinates.
2. WHEN a traveler applies a city or category map filter, THE map service SHALL display markers only for Destination records matching every active map filter.
3. WHEN a traveler selects a map marker, THE Namma Ooru application SHALL display a destination preview and a navigation action to the Destination page.
4. THE Namma Ooru application SHALL access map rendering through a replaceable Map Provider interface.

### Requirement 10: Reviews and Ratings
**User Story:** As a traveler, I want to read and submit Destination reviews, so that I can evaluate places using visitor experience.
#### Acceptance Criteria
1. WHEN a traveler submits a Review with an integer rating from 1 through 5, THE review service SHALL persist the Review against an existing Destination.
2. IF a traveler submits a Review with a rating outside the integer range 1 through 5 or an unknown Destination identifier, THEN THE review service SHALL reject the Review without persistence.
3. WHEN the Namma Ooru application displays Destination reviews, THE Namma Ooru application SHALL display review count, average rating, rating distribution, and recent Reviews.
4. WHEN a Destination has the configured minimum review count, THE AI Provider SHALL return a review summary containing positive themes and concern themes derived only from that Destination’s Reviews.
5. WHEN the Namma Ooru application displays a review summary, THE Namma Ooru application SHALL label the summary as AI-generated.

### Requirement 11: Security and Operational Quality
**User Story:** As a maintainer, I want secure and observable application behavior, so that the application protects credentials and handles failures safely.
#### Acceptance Criteria
1. THE backend API SHALL validate request data at the API boundary before processing data queries or AI prompts.
2. THE deployment configuration SHALL obtain AWS credentials from the standard AWS credential chain or IAM roles.
3. WHEN the backend API encounters an expected validation, dependency, or internal failure, THE backend API SHALL return a structured error containing a public error code and a safe message.
4. WHEN the Namma Ooru application receives a backend API error, THE Namma Ooru application SHALL display an error state with a retry action where retry is valid.
5. THE backend API SHALL restrict cross-origin requests to configured frontend origins.

### Requirement 12: AWS Infrastructure and Deployment
**User Story:** As a maintainer, I want reproducible AWS infrastructure, so that backend and frontend can be deployed independently.
#### Acceptance Criteria
1. THE infrastructure project SHALL define data, AI, backend, frontend, and monitoring resources using AWS CDK v2 with Python 3.9 or later.
2. THE infrastructure project SHALL provision a backend API deployment independently from the frontend deployment.
3. WHEN the backend stack deployment completes, THE infrastructure project SHALL expose the backend API URL as a CloudFormation output for local frontend configuration.
4. THE infrastructure project SHALL grant each AWS role only the resource permissions required by its component.
5. WHEN the frontend deployment is enabled, THE infrastructure project SHALL deploy the frontend through AWS Amplify Hosting using the backend API URL configuration.

### Requirement 13: Kiro University Evidence
**User Story:** As a challenge reviewer, I want retained Kiro artifacts, so that I can verify the project used all required Kiro lessons.
#### Acceptance Criteria
1. THE repository SHALL retain requirements, design, and task documents under `.kiro/specs/namma-ooru/`.
2. THE repository SHALL retain product, architecture, coding, UI, AI, security, testing, and data guidance under `.kiro/steering/`.
3. THE repository SHALL retain executable quality, test, data-validation, and completion hooks under `.kiro/hooks/`.
4. THE repository SHALL retain a Namma Ooru Power and its destination-curation, itinerary-planning, travel-content, and review-analysis skills.
5. THE repository SHALL retain MCP usage evidence and Custom Agent definitions with scoped responsibilities.
6. THE repository SHALL retain property-test implementation evidence that maps each implemented property to its design property and acceptance criteria.
