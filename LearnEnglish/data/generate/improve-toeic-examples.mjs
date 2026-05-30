import fs from "node:fs/promises";

const FILE = "toeic-basic-english-premium.json";
const KEY = "toeic-basic-english-premium";

const phraseOverrides = {
  "minutes": "the meeting minutes",
  "wake-up": "the wake-up call",
  "raw": "the raw material",
  "checkin": "the check-in process",
  "checkout": "the checkout process",
  "takeout": "the takeout order",
};

const topicTemplates = {
  business: [
    "The director reviewed {term} before approving the new plan.",
    "Several managers discussed {term} during the Monday briefing.",
    "The team updated {term} after the client changed the request.",
    "A clear note about {term} helped everyone make a faster decision.",
    "The supervisor asked for details about {term} before the deadline.",
  ],
  office: [
    "The clerk placed {term} on the reception desk before lunch.",
    "Please send {term} to the front office before the end of the day.",
    "The assistant organized {term} so the manager could find it quickly.",
    "A staff member checked {term} while preparing the morning paperwork.",
    "The office team used {term} to finish the administrative task.",
  ],
  meetings: [
    "Each attendee received {term} at the conference entrance.",
    "The speaker mentioned {term} during the afternoon session.",
    "The host prepared {term} before the seminar began.",
    "Participants asked questions about {term} after the presentation.",
    "The event planner confirmed {term} with the venue manager.",
  ],
  employment: [
    "The recruiter reviewed {term} before scheduling the interview.",
    "Human resources updated {term} for the new employee.",
    "The candidate asked about {term} during the final interview.",
    "The manager discussed {term} with the trainee on Friday.",
    "The company changed {term} after reviewing staff feedback.",
  ],
  finance: [
    "The accountant checked {term} before closing the monthly report.",
    "The bank officer explained {term} to the business owner.",
    "The finance team compared {term} with last year's figures.",
    "The cashier printed {term} after receiving the payment.",
    "The manager reviewed {term} before approving the budget.",
  ],
  marketing: [
    "The marketing team tested {term} before the product launch.",
    "Customers noticed {term} in the new advertising campaign.",
    "The retailer used {term} to attract more shoppers.",
    "The survey showed that {term} influenced customer choices.",
    "The brand manager adjusted {term} after reviewing sales data.",
  ],
  "customer-service": [
    "The representative handled {term} politely during the call.",
    "The support team logged {term} in the customer service system.",
    "The customer received {term} after contacting the helpline.",
    "The operator explained {term} clearly before ending the conversation.",
    "A quick response about {term} improved customer satisfaction.",
  ],
  shopping: [
    "The shopper checked {term} before going to the checkout counter.",
    "The store manager updated {term} on the sales floor.",
    "The cashier scanned {term} and placed it in the bag.",
    "Customers compared {term} while looking through the aisle.",
    "The vendor prepared {term} for the weekend sale.",
  ],
  travel: [
    "The traveler checked {term} before leaving for the airport.",
    "The agency confirmed {term} for the business trip.",
    "The guide explained {term} during the city tour.",
    "Passengers asked about {term} at the terminal desk.",
    "The itinerary included {term} for the first day of travel.",
  ],
  hotels: [
    "The receptionist confirmed {term} when the guest arrived.",
    "Housekeeping reported {term} to the front desk.",
    "The hotel manager checked {term} before assigning the room.",
    "The guest asked about {term} during check-in.",
    "The concierge arranged {term} for a visitor staying overnight.",
  ],
  restaurants: [
    "The server brought {term} to the table before the main course.",
    "The chef prepared {term} for the lunch menu.",
    "The customer asked about {term} before placing an order.",
    "The cafeteria manager checked {term} before opening.",
    "The kitchen staff cleaned {term} after the dinner rush.",
  ],
  transportation: [
    "The passenger checked {term} before boarding the train.",
    "The driver reported {term} to the transportation office.",
    "Commuters waited near {term} during the morning delay.",
    "The station clerk explained {term} to a new traveler.",
    "The route planner adjusted {term} because of heavy traffic.",
  ],
  shipping: [
    "The warehouse clerk checked {term} before loading the truck.",
    "The courier updated {term} after picking up the parcel.",
    "The shipping team recorded {term} on the delivery form.",
    "The supplier confirmed {term} before sending the shipment.",
    "The logistics manager reviewed {term} at the port.",
  ],
  manufacturing: [
    "The inspector checked {term} before the product left the factory.",
    "The technician adjusted {term} during the production shift.",
    "The plant manager discussed {term} with the assembly team.",
    "Workers reported {term} after testing the equipment.",
    "The manufacturer improved {term} to reduce defects.",
  ],
  technology: [
    "The technician updated {term} before restarting the computer.",
    "The support team checked {term} after the system error.",
    "The employee entered {term} to access the company network.",
    "The IT manager explained {term} during the training session.",
    "The software team tested {term} before releasing the update.",
  ],
  "real-estate": [
    "The agent described {term} during the property tour.",
    "The tenant asked about {term} before signing the lease.",
    "The building manager inspected {term} on Monday morning.",
    "The landlord repaired {term} before the new resident moved in.",
    "The facility report included notes about {term}.",
  ],
  healthcare: [
    "The patient asked about {term} before the appointment.",
    "The physician explained {term} during the examination.",
    "The clinic recorded {term} in the patient's file.",
    "The insurance provider reviewed {term} before approving the claim.",
    "The pharmacy checked {term} before preparing the medicine.",
  ],
  training: [
    "The instructor explained {term} at the beginning of the course.",
    "Students practiced {term} during the training session.",
    "The trainer added {term} to the workshop materials.",
    "The registration desk confirmed {term} for each participant.",
    "The lesson included {term} as part of the final exercise.",
  ],
  legal: [
    "The lawyer reviewed {term} before the agreement was signed.",
    "The compliance team explained {term} to the department head.",
    "The notice included {term} in clear legal language.",
    "The company updated {term} after the regulation changed.",
    "The witness mentioned {term} during the formal review.",
  ],
  safety: [
    "The safety officer reported {term} after the inspection.",
    "Employees reviewed {term} before entering the work area.",
    "The supervisor posted {term} near the factory entrance.",
    "The training session explained {term} for emergency situations.",
    "The team followed {term} to prevent accidents.",
  ],
  procurement: [
    "The purchasing team reviewed {term} before choosing a supplier.",
    "The buyer requested {term} from three vendors.",
    "The procurement officer compared {term} during the selection process.",
    "The manager approved {term} after checking the contract terms.",
    "The supplier sent {term} with the updated price list.",
  ],
  accounting: [
    "The accountant entered {term} into the monthly ledger.",
    "The auditor checked {term} before completing the report.",
    "The finance office adjusted {term} after reviewing the invoice.",
    "The company tracked {term} for the end-of-year statement.",
    "The controller explained {term} during the accounting review.",
  ],
  "project-management": [
    "The project manager added {term} to the weekly status report.",
    "The team discussed {term} during the kickoff meeting.",
    "The roadmap changed after the client reviewed {term}.",
    "The coordinator tracked {term} until the task was completed.",
    "The stakeholder asked for an update about {term}.",
  ],
  leadership: [
    "The executive discussed {term} with the department managers.",
    "The board reviewed {term} before making a decision.",
    "The team leader used {term} to improve performance.",
    "The officer explained {term} during the management meeting.",
    "The chairperson asked for more details about {term}.",
  ],
  "human-resources": [
    "Human resources updated {term} after the policy review.",
    "The manager discussed {term} with the new employee.",
    "The staff handbook explained {term} in simple language.",
    "The recruiter considered {term} during the screening process.",
    "The supervisor reported {term} to the personnel office.",
  ],
  economics: [
    "The economist analyzed {term} in the quarterly report.",
    "The market report showed a change in {term}.",
    "The analyst compared {term} across several business sectors.",
    "The government data helped explain {term}.",
    "Investors watched {term} closely during the recovery period.",
  ],
  media: [
    "The editor approved {term} before the newsletter was published.",
    "The reporter mentioned {term} in the morning broadcast.",
    "The public relations team prepared {term} for the announcement.",
    "Readers responded to {term} in the company magazine.",
    "The advertiser revised {term} before the campaign went live.",
  ],
  communication: [
    "The employee checked {term} before joining the teleconference.",
    "The receptionist used {term} to contact the sales team.",
    "The technician fixed {term} after the call dropped.",
    "The message about {term} was sent to every department.",
    "The manager confirmed {term} during the phone conversation.",
  ],
  research: [
    "The analyst included {term} in the research report.",
    "The laboratory team measured {term} during the trial.",
    "The survey results supported {term} in the final conclusion.",
    "The researcher checked {term} before publishing the findings.",
    "The recommendation was based on {term} from several sources.",
  ],
  data: [
    "The analyst checked {term} on the company dashboard.",
    "The system administrator updated {term} before the backup.",
    "The security team reviewed {term} after the login issue.",
    "The developer tested {term} before uploading the file.",
    "The report used {term} to explain the monthly results.",
  ],
  banking: [
    "The teller checked {term} before completing the transaction.",
    "The bank manager explained {term} to the small business owner.",
    "The borrower asked about {term} during the loan meeting.",
    "The finance clerk recorded {term} in the banking system.",
    "The notary confirmed {term} before the wire transfer.",
  ],
  investment: [
    "The broker reviewed {term} before calling the investor.",
    "The portfolio manager compared {term} with market expectations.",
    "The shareholder asked about {term} during the annual meeting.",
    "The analyst tracked {term} after the stock price changed.",
    "The prospectus explained {term} for potential investors.",
  ],
  insurance: [
    "The adjuster reviewed {term} before approving the claim.",
    "The insurer explained {term} to the policyholder.",
    "The customer asked about {term} before renewing the plan.",
    "The report described {term} after the accident.",
    "The underwriter checked {term} before issuing the policy.",
  ],
  construction: [
    "The contractor inspected {term} before work began.",
    "The engineer checked {term} at the construction site.",
    "The architect discussed {term} with the project owner.",
    "The crew repaired {term} before the building inspection.",
    "The site manager ordered {term} for the next phase.",
  ],
  maintenance: [
    "The technician checked {term} during the maintenance visit.",
    "The repair team reported {term} to the facility manager.",
    "The worker replaced {term} before the equipment restarted.",
    "The diagnostic report identified {term} as the problem.",
    "The janitor cleaned {term} after the service call.",
  ],
  energy: [
    "The utility company monitored {term} during peak demand.",
    "The engineer inspected {term} before restoring power.",
    "The energy report compared {term} with last month's usage.",
    "The technician tested {term} at the power station.",
    "The city invested in {term} to reduce fuel costs.",
  ],
  agriculture: [
    "The farmer checked {term} before the morning harvest.",
    "The agricultural report described {term} for the season.",
    "Workers prepared {term} near the greenhouse.",
    "The buyer inspected {term} before placing a large order.",
    "The farm manager used {term} to improve production.",
  ],
  "food-preparation": [
    "The chef prepared {term} before the restaurant opened.",
    "The kitchen staff checked {term} during food preparation.",
    "The menu described {term} for customers with allergies.",
    "The baker used {term} for the morning order.",
    "The cook cleaned {term} after finishing the recipe.",
  ],
  "healthcare-advanced": [
    "The nurse recorded {term} before the doctor arrived.",
    "The specialist explained {term} during the consultation.",
    "The hospital updated {term} in the patient's chart.",
    "The surgeon reviewed {term} before the operation.",
    "The paramedic reported {term} to the emergency room staff.",
  ],
  "public-services": [
    "The council discussed {term} during the public meeting.",
    "Citizens asked about {term} at the government office.",
    "The mayor announced {term} in the city newsletter.",
    "The committee reviewed {term} before the election.",
    "The ministry published {term} for local residents.",
  ],
};

const sceneByTopic = {
  business: "planning meeting",
  office: "administrative review",
  meetings: "conference session",
  employment: "hiring discussion",
  finance: "monthly finance review",
  marketing: "campaign meeting",
  "customer-service": "support call",
  shopping: "store review",
  travel: "travel briefing",
  hotels: "front desk meeting",
  restaurants: "restaurant shift meeting",
  transportation: "transportation update",
  shipping: "logistics review",
  manufacturing: "factory briefing",
  technology: "IT support session",
  "real-estate": "property review",
  healthcare: "clinic appointment",
  training: "training session",
  legal: "compliance review",
  safety: "safety briefing",
  procurement: "supplier review",
  accounting: "accounting review",
  "project-management": "project update",
  leadership: "management meeting",
  "human-resources": "HR meeting",
  economics: "market analysis",
  media: "public relations meeting",
  communication: "team call",
  research: "research review",
  data: "data review",
  banking: "banking appointment",
  investment: "investment review",
  insurance: "policy review",
  construction: "site meeting",
  maintenance: "maintenance visit",
  energy: "utility review",
  agriculture: "farm report",
  "food-preparation": "kitchen briefing",
  "healthcare-advanced": "hospital consultation",
  "public-services": "public office meeting",
};

const actorByTopic = {
  business: "director",
  office: "office assistant",
  meetings: "event coordinator",
  employment: "recruiter",
  finance: "accountant",
  marketing: "marketing manager",
  "customer-service": "service representative",
  shopping: "store manager",
  travel: "travel agent",
  hotels: "front desk clerk",
  restaurants: "restaurant manager",
  transportation: "route planner",
  shipping: "warehouse clerk",
  manufacturing: "production supervisor",
  technology: "IT technician",
  "real-estate": "property manager",
  healthcare: "clinic coordinator",
  training: "instructor",
  legal: "compliance officer",
  safety: "safety officer",
  procurement: "purchasing manager",
  accounting: "auditor",
  "project-management": "project manager",
  leadership: "executive",
  "human-resources": "HR manager",
  economics: "market analyst",
  media: "editor",
  communication: "receptionist",
  research: "research analyst",
  data: "system analyst",
  banking: "bank teller",
  investment: "portfolio manager",
  insurance: "claims adjuster",
  construction: "site manager",
  maintenance: "maintenance technician",
  energy: "utility engineer",
  agriculture: "farm manager",
  "food-preparation": "chef",
  "healthcare-advanced": "nurse",
  "public-services": "city official",
};

const placeByTopic = {
  business: "conference room",
  office: "front office",
  meetings: "event hall",
  employment: "interview room",
  finance: "finance office",
  marketing: "sales meeting",
  "customer-service": "support desk",
  shopping: "retail store",
  travel: "airport counter",
  hotels: "hotel lobby",
  restaurants: "dining room",
  transportation: "station office",
  shipping: "warehouse",
  manufacturing: "factory floor",
  technology: "IT department",
  "real-estate": "building office",
  healthcare: "clinic",
  training: "training room",
  legal: "legal office",
  safety: "work site",
  procurement: "purchasing office",
  accounting: "accounting department",
  "project-management": "project room",
  leadership: "boardroom",
  "human-resources": "HR office",
  economics: "research department",
  media: "newsroom",
  communication: "reception area",
  research: "laboratory",
  data: "operations center",
  banking: "bank branch",
  investment: "investment office",
  insurance: "claims office",
  construction: "construction site",
  maintenance: "service area",
  energy: "power station",
  agriculture: "farm office",
  "food-preparation": "kitchen",
  "healthcare-advanced": "hospital ward",
  "public-services": "city hall",
};

const documentByTopic = {
  business: "planning report",
  office: "office memo",
  meetings: "event schedule",
  employment: "hiring file",
  finance: "monthly statement",
  marketing: "campaign report",
  "customer-service": "support ticket",
  shopping: "sales report",
  travel: "travel itinerary",
  hotels: "guest record",
  restaurants: "shift report",
  transportation: "route notice",
  shipping: "shipping form",
  manufacturing: "inspection report",
  technology: "system log",
  "real-estate": "property file",
  healthcare: "patient record",
  training: "course handout",
  legal: "compliance document",
  safety: "safety notice",
  procurement: "purchase request",
  accounting: "audit report",
  "project-management": "status report",
  leadership: "management summary",
  "human-resources": "employee file",
  economics: "market report",
  media: "press note",
  communication: "call log",
  research: "research paper",
  data: "dashboard report",
  banking: "bank record",
  investment: "portfolio summary",
  insurance: "claim file",
  construction: "site report",
  maintenance: "service report",
  energy: "utility report",
  agriculture: "harvest report",
  "food-preparation": "menu note",
  "healthcare-advanced": "medical chart",
  "public-services": "public notice",
};

const safeTemplates = [
  "During the {scene}, the {actor} checked the latest details about {term}.",
  "The {document} explained why {term} mattered to the team.",
  "Staff at the {place} asked a practical question about {term}.",
  "Before the deadline, the {actor} checked the notes about {term}.",
  "A short update on {term} helped the team avoid confusion.",
  "The {actor} mentioned {term} while reviewing the morning schedule.",
  "Everyone at the {place} received a reminder about {term}.",
  "The {document} listed two changes related to {term}.",
  "A customer asked the {actor} for more information about {term}.",
  "The team compared last month's results with the new data on {term}.",
  "The {actor} added a comment about {term} to the {document}.",
  "Several employees discussed {term} after the staff meeting.",
  "The notice near the {place} gave clear instructions about {term}.",
  "The {actor} confirmed the details of {term} by phone.",
  "A delay occurred because the team needed more information about {term}.",
  "The {document} showed that {term} had changed since last week.",
  "Visitors to the {place} were asked to check the notice about {term}.",
  "The {actor} prepared a brief explanation of {term} for new staff.",
  "The team saved the updated record for {term} before leaving.",
  "An email about {term} was sent to every department.",
  "The {actor} answered three questions about {term} during the call.",
  "The {document} included a clear deadline related to {term}.",
  "Staff reviewed information about {term} before approving the request.",
  "The {actor} asked another department to verify information about {term}.",
  "The final report included a short summary of {term}.",
];

function termFor(entry) {
  const word = entry.word.toLowerCase();
  return phraseOverrides[word] || `the ${entry.word}`;
}

function buildExample(entry, indexInTopic) {
  if (!topicTemplates[entry.topic]) throw new Error(`Missing templates for topic: ${entry.topic}`);
  const scene = sceneByTopic[entry.topic];
  if (!scene) throw new Error(`Missing scene for topic: ${entry.topic}`);
  const actor = actorByTopic[entry.topic];
  const place = placeByTopic[entry.topic];
  const document = documentByTopic[entry.topic];
  if (!actor || !place || !document) throw new Error(`Missing topic metadata for topic: ${entry.topic}`);
  return safeTemplates[indexInTopic % safeTemplates.length]
    .replace("{scene}", scene)
    .replaceAll("{actor}", actor)
    .replaceAll("{place}", place)
    .replaceAll("{document}", document)
    .replaceAll("{term}", termFor(entry));
}

const data = JSON.parse(await fs.readFile(FILE, "utf8"));
const entries = data[KEY];
const topicCounts = new Map();
const examples = new Set();

for (const entry of entries) {
  const indexInTopic = topicCounts.get(entry.topic) || 0;
  topicCounts.set(entry.topic, indexInTopic + 1);
  entry.example = buildExample(entry, indexInTopic);
  if (examples.has(entry.example)) throw new Error(`Duplicate example: ${entry.example}`);
  examples.add(entry.example);
}

const remainingGeneric = entries.filter((entry) => /context\.$/.test(entry.example));
if (remainingGeneric.length > 0) {
  throw new Error(`${remainingGeneric.length} examples still end with generic context wording`);
}

await fs.writeFile(FILE, `${JSON.stringify(data, null, 2)}\n`, "utf8");

console.log(JSON.stringify({
  file: FILE,
  updatedExamples: entries.length,
  uniqueExamples: examples.size,
  topics: topicCounts.size,
}, null, 2));
