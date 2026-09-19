/**
 * Canonical Job & Internship Description Presentation Normalizer.
 *
 * Normalizes raw ATS descriptions into RoleRadar's structured canonical sections:
 * - Job Summary / Overview
 * - Core Responsibilities
 * - Required Skills & Technologies
 * - Preferred Skills
 * - Qualifications & Educational Requirements
 * - Additional Information
 * - Detailed Description
 *
 * Removes redundant provider headings (e.g., repeated "JOB DESCRIPTION", "QUALIFICATIONS"),
 * strips inline heading artifacts with colons, avoids repeating content already displayed in
 * canonical cards, and ensures no empty UI sections are rendered.
 */

export interface NormalizedItem {
  isBullet: boolean;
  text: string;
}

export interface NormalizedSection {
  title?: string;
  items: NormalizedItem[];
}

export interface JobPresentationResult {
  summary?: NormalizedSection;
  responsibilities: string[];
  qualifications: string[];
  additionalInfo?: NormalizedSection;
  detailedSections: NormalizedSection[];
}

const FORBIDDEN_METADATA_PATTERNS = [
  /^\s*(?:tariff\s*area|legal\s*entity(?:\s*\(acronym\))?|global\s*salary(?:\s*level)?|division(?:\s*full\s*name|\s*identifiers)?|local\s*grade|cost\s*center|entity\s*acronym|direct\s*or\s*indirect|working\s*(?:location|country|hours)|position\s*type|brands)\s*[:\-]/i,
];

// Patterns identifying section heading lines
const HEADING_PATTERNS: { category: string; regex: RegExp }[] = [
  {
    category: "overview",
    regex: /^(?:company\s*description|about\s*(?:the\s*)?company|about\s*us|who\s*we\s*are|who\s*are\s*we|the\s*opportunity|role\s*overview|job\s*summary|overview|about\s*the\s*role|summary)\s*[:\-]?$/i,
  },
  {
    category: "responsibilities",
    regex: /^(?:job\s*description|role\s*description|what\s*you(?:'ll|’ll|\s*will)\s*do|key\s*responsibilities|responsibilities|tasks\s*(?:\/|and)\s*responsibilities|duties|roles?\s*and\s*responsibilities)\s*[:\-]?$/i,
  },
  {
    category: "requirements",
    regex: /^(?:requirements|must\s*have(?:\s*qualifications)?|required\s*skills(?:\s*set)?|expected\s*skill\s*set|expected\s*skills|technical\s*skillset|key\s*skills|what\s*you(?:'ll|’ll|\s*will)\s*need|minimum\s*qualifications|basic\s*qualifications)\s*[:\-]?$/i,
  },
  {
    category: "preferred",
    regex: /^(?:preferred\s*qualifications|nice[- ]to[- ]have|good\s*to\s*have|bonus\s*points|desired\s*skills|preferred\s*skills|plus)\s*[:\-]?$/i,
  },
  {
    category: "qualifications",
    regex: /^(?:qualifications?|educational\s*requirements?|education(?:\s*and\s*experience)?|eligibility)\s*[:\-]?$/i,
  },
  {
    category: "additional",
    regex: /^(?:additional\s*information(?:\s*\/\s*experience)?|what\s*else\??|benefits|perks|working\s*conditions|other\s*skills|our\s*values|equal\s*opportunity|eeo\s*statement)\s*[:\-]?$/i,
  },
];

function cleanRawText(raw: string): string {
  if (!raw) return "";
  let text = raw
    .replace(/&amp;/g, "&")
    .replace(/&quot;/g, '"')
    .replace(/&#xa0;/g, " ")
    .replace(/&nbsp;/g, " ")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/[\s\xa0]*[\u00d8\ufffd•][\s\xa0]*/g, "\n- ")
    .replace(/[\u00b7·]/g, "\n- ");

  // Strip forbidden internal ATS metadata lines
  const lines = text.split("\n").filter((l) => !FORBIDDEN_METADATA_PATTERNS.some((pat) => pat.test(l)));
  return lines.join("\n").trim();
}

function normalizeKey(str: string): string {
  return str.toLowerCase().replace(/[^a-z0-9]/g, "");
}

function matchCategory(line: string): string | null {
  const clean = line.replace(/^#+\s*/, "").replace(/[:\-]+$/, "").trim();
  if (!clean || clean.length > 70) return null;
  for (const hp of HEADING_PATTERNS) {
    if (hp.regex.test(clean)) {
      return hp.category;
    }
  }
  return null;
}

export function normalizeJobDescriptionPresentation(params: {
  description: string;
  responsibilities?: string[];
  qualifications?: string[];
  skillsRequired?: string[];
  skillsNiceToHave?: string[];
}): JobPresentationResult {
  const { description, responsibilities = [], qualifications = [], skillsRequired = [], skillsNiceToHave = [] } = params;

  const rawClean = cleanRawText(description);
  if (!rawClean) {
    return {
      responsibilities: responsibilities.filter(Boolean),
      qualifications: qualifications.filter(Boolean),
      detailedSections: [],
    };
  }

  // Canonical sets for deduplication
  const respSet = new Set(responsibilities.map(normalizeKey).filter(Boolean));
  const qualSet = new Set(qualifications.map(normalizeKey).filter(Boolean));
  const skillSet = new Set([...skillsRequired, ...skillsNiceToHave].map(normalizeKey).filter(Boolean));

  // Partition raw description into semantic blocks
  // Pre-process inline subheadings: ensure they start on a new line
  const textWithNormalizedSubheadings = rawClean.replace(
    /(?:\r?\n|^|\.\s+)(Expected skill set|Tasks\s*\/\s*Responsibilities|Good to have|Job Description|Qualifications|Required skills|Key skills)\s*:\s*/gi,
    "\n\n$1:\n"
  );

  const rawLines = textWithNormalizedSubheadings.split("\n").map((l) => l.trim()).filter(Boolean);

  interface RawSection {
    category: string; // 'overview' | 'responsibilities' | 'requirements' | 'preferred' | 'qualifications' | 'additional' | 'other'
    title?: string;
    items: NormalizedItem[];
  }

  const sections: RawSection[] = [];
  let currentSec: RawSection = { category: "other", title: "", items: [] };

  for (const line of rawLines) {
    const isMdHeading = line.startsWith("#");
    const detectedCat = matchCategory(line);

    if (isMdHeading || detectedCat) {
      if (currentSec.items.length > 0 || currentSec.title) {
        sections.push(currentSec);
      }
      const titleClean = line.replace(/^#+\s*/, "").replace(/[:\-]+$/, "").trim();
      currentSec = {
        category: detectedCat || "other",
        title: titleClean,
        items: [],
      };
      continue;
    }

    // Check if line is an inline redundant heading inside a section
    // e.g., "Job Description:" or "JOB DESCRIPTION" appearing inside an already started section
    const inlineCat = matchCategory(line);
    if (inlineCat && line.length < 50 && !line.includes(".")) {
      // If it's a redundant repetition of the current section category or a generic heading, skip it!
      if (inlineCat === currentSec.category || inlineCat === "responsibilities" || inlineCat === "qualifications") {
        continue;
      }
    }

    const isBullet = line.startsWith("- ") || line.startsWith("* ") || line.startsWith("• ");
    const textClean = line.replace(/^[-*•]\s+/, "").trim();
    if (textClean) {
      currentSec.items.push({ isBullet, text: textClean });
    }
  }

  if (currentSec.items.length > 0 || currentSec.title) {
    sections.push(currentSec);
  }

  // Deduplicate and assemble canonical sections
  let summarySec: NormalizedSection | undefined;
  let additionalSec: NormalizedSection | undefined;
  const detailedSections: NormalizedSection[] = [];

  // Fallback responsibilities / qualifications if canonical was empty
  const finalResponsibilities = [...responsibilities];
  const finalQualifications = [...qualifications];

  for (const sec of sections) {
    // 1. Overview / Summary section
    if (sec.category === "overview") {
      if (!summarySec && sec.items.length > 0) {
        summarySec = {
          title: "Job Summary",
          items: sec.items,
        };
      } else if (sec.items.length > 0) {
        // Subsequent overview content goes to detailed description under "Role Overview" to avoid duplicate "Job Summary" title
        detailedSections.push({ title: "Role Overview", items: sec.items });
      }
      continue;
    }

    // 2. Responsibilities section
    if (sec.category === "responsibilities") {
      for (const item of sec.items) {
        const k = normalizeKey(item.text);
        if (!k) continue;

        // If item is role logistics/metadata (e.g. "Location: ...", "Job position: ..."), route to additionalSec
        if (/^(?:job\s*position|location|department|experience|employment\s*type|contract\s*type)\s*[:\-].*/i.test(item.text.trim())) {
          if (!additionalSec) {
            additionalSec = { title: "Additional Information", items: [item] };
          } else {
            additionalSec.items.push(item);
          }
          continue;
        }

        if (item.isBullet || item.text.split(" ").length < 35) {
          if (!respSet.has(k)) {
            finalResponsibilities.push(item.text);
            respSet.add(k);
          }
        } else {
          if (!respSet.has(k)) {
            detailedSections.push({ title: "Role Context", items: [item] });
          }
        }
      }
      continue;
    }

    // 3. Qualifications section
    if (sec.category === "qualifications") {
      for (const item of sec.items) {
        const k = normalizeKey(item.text);
        if (!k) continue;
        if (item.isBullet || item.text.split(" ").length < 35) {
          if (!qualSet.has(k)) {
            finalQualifications.push(item.text);
            qualSet.add(k);
          }
        } else {
          if (!qualSet.has(k)) {
            detailedSections.push({ title: "Qualifications Context", items: [item] });
          }
        }
      }
      continue;
    }

    // 4. Requirements / Skills section
    if (sec.category === "requirements" || sec.category === "preferred") {
      // Filter out items that merely list skills already shown in Required Skills card
      const uniqueItems = sec.items.filter((item) => {
        const k = normalizeKey(item.text);
        return !skillSet.has(k);
      });

      // If there are detailed items (e.g. descriptive requirement sentences) that aren't just single skill chips, keep them
      const nonChipItems = uniqueItems.filter((item) => item.text.split(" ").length > 4 || !skillSet.has(normalizeKey(item.text)));
      if (nonChipItems.length > 0) {
        detailedSections.push({
          title: sec.category === "preferred" ? "Preferred Profile Details" : "Requirement Details",
          items: nonChipItems,
        });
      }
      continue;
    }

    // 5. Additional Information / Logistics / Perks
    if (sec.category === "additional") {
      if (!additionalSec && sec.items.length > 0) {
        additionalSec = {
          title: "Additional Information",
          items: sec.items,
        };
      } else if (sec.items.length > 0 && additionalSec) {
        additionalSec.items.push(...sec.items);
      }
      continue;
    }

    // 6. Other narrative content
    if (sec.items.length > 0) {
      const titleLower = (sec.title || "").toLowerCase().trim();
      const isRedundantHeading = [
        "job description",
        "role description",
        "qualifications",
        "qualification",
        "requirements",
        "details",
        "additional information",
      ].some((h) => titleLower === h || titleLower.startsWith(h + ":"));

      detailedSections.push({
        title: isRedundantHeading ? undefined : sec.title,
        items: sec.items,
      });
    }
  }

  // Deduplicate consecutive detailed sections that have the same title
  const finalDetailed: NormalizedSection[] = [];
  for (const ds of detailedSections) {
    if (ds.items.length === 0) continue;
    const last = finalDetailed[finalDetailed.length - 1];
    if (last && last.title && ds.title && last.title.toLowerCase() === ds.title.toLowerCase()) {
      // Merge items into previous section instead of repeating heading
      last.items.push(...ds.items);
    } else {
      finalDetailed.push(ds);
    }
  }

  return {
    summary: summarySec && summarySec.items.length > 0 ? summarySec : undefined,
    responsibilities: finalResponsibilities,
    qualifications: finalQualifications,
    additionalInfo: additionalSec && additionalSec.items.length > 0 ? additionalSec : undefined,
    detailedSections: finalDetailed,
  };
}
