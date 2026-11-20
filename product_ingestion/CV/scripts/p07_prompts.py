"""Zero-shot text prompts per attribute group (class -> list of descriptions; templates wrap them)."""

PATTERN = {
    "plain": ["a plain solid colour garment with no pattern", "an unpatterned plain garment"],
    "stripe": ["a striped garment", "a garment with stripes"],
    "floral": ["a garment with a floral print", "a flower pattern garment"],
    "check": ["a checked plaid garment", "a garment with a gingham or tartan check pattern"],
    "dot": ["a polka dot garment", "a garment with dots"],
    "geometric": ["a garment with a geometric pattern", "a garment with a zigzag or diamond pattern"],
    "abstract": ["a garment with an abstract print", "a garment with a painterly abstract pattern"],
    "text": ["a garment with printed text, letters or numbers", "a t-shirt with a slogan written on it"],
    "graphic": ["a garment with a cartoon graphic print", "a t-shirt with a cartoon character picture"],
    "other": ["a garment with a paisley, camouflage or animal print", "a leopard or camouflage patterned garment"],
}
SLEEVE = {
    "sleeveless": ["a sleeveless top with no sleeves", "a tank top"],
    "short": ["a top with short sleeves", "a short-sleeved t-shirt"],
    "elbow": ["a top with elbow-length sleeves", "sleeves ending at the elbow"],
    "three_quarter": ["a top with three-quarter length sleeves", "sleeves ending below the elbow above the wrist"],
    "long": ["a top with long sleeves to the wrist", "a long-sleeved shirt"],
}
SLEEVE3 = {
    "short_or_none": ["a top with short sleeves or no sleeves"],
    "mid": ["a top with elbow-length or three-quarter sleeves"],
    "long": ["a top with long sleeves to the wrist"],
}
NECK = {
    "round_crew": ["a round crew neckline", "a crew neck"],
    "scoop_u": ["a scoop neckline", "a u-neck neckline"],
    "v_neck": ["a v-neck neckline", "a deep plunging v neckline"],
    "wide": ["a wide boat or off-the-shoulder neckline", "a straight across or square neckline"],
    "sweetheart": ["a sweetheart neckline"],
    "high_neck": ["a turtleneck or high neck", "a cowl neck"],
    "halter": ["a halter neckline"],
    "collarless": ["a collarless neckline with an open front"],
}
TEMPLATES = {
    "pattern": ["a photo of {}.", "{}"],
    "sleeve": ["a photo of {}.", "{}"],
    "sleeve3": ["a photo of {}.", "{}"],
    "neckline": ["a close-up photo of {}.", "{}"],
}
PROMPTS = {
    "pattern": (PATTERN, TEMPLATES["pattern"]),
    "sleeve": (SLEEVE, TEMPLATES["sleeve"]),
    "sleeve3": (SLEEVE3, TEMPLATES["sleeve3"]),
    "neckline": (NECK, TEMPLATES["neckline"]),
}
