type CompensationRecord = {
  job_type?: string | null;
  opportunity_type?: string | null;
  salary_min?: number | null;
  salary_max?: number | null;
  salary_currency?: string | null;
  salary_period?: string | null;
  salary_unit?: string | null;
  stipend?: number | null;
  stipend_min?: number | null;
  stipend_max?: number | null;
  stipend_currency?: string | null;
  stipend_period?: string | null;
  stipend_unit?: string | null;
  compensation_type?: string | null;
  compensation_text?: string | null;
};

function formatAmount(amount: number, currency: string | null | undefined): string {
  if (!currency) return amount.toLocaleString("en-IN", { maximumFractionDigits: 2 });
  return new Intl.NumberFormat(currency === "INR" ? "en-IN" : "en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(amount);
}

function formatPeriod(period: string | null | undefined): string {
  const suffixes: Record<string, string> = {
    YEAR: "/year",
    MONTH: "/month",
    WEEK: "/week",
    DAY: "/day",
    HOUR: "/hour",
  };
  return period ? suffixes[period.toUpperCase()] ?? `/${period}` : "";
}

function formatRange(minimum: number, maximum: number | null | undefined, currency: string | null | undefined): string {
  const low = formatAmount(minimum, currency);
  if (maximum == null || maximum === minimum) return low;
  return `${low}–${formatAmount(maximum, currency)}`;
}

export function formatCompensation(job: CompensationRecord): string {
  const isInternship = job.job_type === "internship" || job.opportunity_type === "INTERNSHIP";
  const hasStipend = job.stipend != null || job.stipend_min != null || job.stipend_max != null;

  if (hasStipend || job.compensation_type === "STIPEND") {
    const minimum = job.stipend_min ?? job.stipend;
    if (minimum != null) {
      const range = job.stipend_unit === "LPA"
        ? `${formatAmount(minimum, job.stipend_currency)}${job.stipend_max != null && job.stipend_max !== minimum ? `–${formatAmount(job.stipend_max, job.stipend_currency)}` : ""} LPA`
        : `${formatRange(minimum, job.stipend_max, job.stipend_currency)}${formatPeriod(job.stipend_period)}`;
      return range;
    }
  }

  if (job.salary_min != null || job.salary_max != null) {
    const minimum = job.salary_min ?? job.salary_max!;
    if (job.salary_unit === "LPA") {
      const suffix = job.salary_currency === "INR" ? " LPA" : ` ${job.salary_currency ?? ""} LPA`;
      const maximum = job.salary_max;
      return `${formatAmount(minimum, job.salary_currency)}${maximum != null && maximum !== minimum ? `–${formatAmount(maximum, job.salary_currency)}` : ""}${suffix}`;
    }
    if (job.salary_unit === "LAKH") {
      const maximum = job.salary_max;
      return `${formatAmount(minimum, job.salary_currency)}${maximum != null && maximum !== minimum ? `–${formatAmount(maximum, job.salary_currency)}` : ""} lakh${formatPeriod(job.salary_period)}`;
    }
    return `${formatRange(minimum, job.salary_max, job.salary_currency)}${formatPeriod(job.salary_period)}`;
  }

  if (job.compensation_text) return job.compensation_text;
  return isInternship ? "Stipend not disclosed" : "Salary not disclosed";
}