import { useEffect, useId, useMemo, useRef, useState } from "react";
import { ChevronDown, PenLine, Search, Target } from "lucide-react";
import { ALL_JOB_ROLES } from "../../lib/roleConstants";

export type RoleOption = {
  role: string;
  domain?: string;
  subdomain?: string;
  aliases?: string[];
};

type RoleOptionInput = string | RoleOption;

interface RoleDropdownSelectorProps {
  label?: string;
  selectedRole: string;
  onRoleChange: (newRole: string) => void;
  roles?: RoleOptionInput[];
  includeAllOption?: boolean;
  allOptionLabel?: string;
  className?: string;
  helperText?: string;
}

function normalizeRole(value: string): string {
  return value.toLocaleLowerCase().replace(/[^\p{L}\p{N}]+/gu, " ").trim();
}

function getRoleRelevance(option: RoleOption, query: string): number {
  const normalizedQuery = normalizeRole(query);
  if (!normalizedQuery) return 1;

  const roleName = normalizeRole(option.role);
  const searchableText = normalizeRole([
    option.role,
    option.domain,
    option.subdomain,
    ...(option.aliases ?? []),
  ].join(" "));
  if (roleName === normalizedQuery) return 1000;
  if (roleName.startsWith(normalizedQuery)) return 800;
  if (roleName.includes(normalizedQuery)) return 600;

  const aliasNames = (option.aliases ?? []).map(normalizeRole);
  if (aliasNames.includes(normalizedQuery)) return 550;
  if (aliasNames.some((alias) => alias.startsWith(normalizedQuery))) return 450;
  if (aliasNames.some((alias) => alias.includes(normalizedQuery))) return 350;

  const tokens = normalizedQuery.split(/\s+/);
  return tokens.every((token) => searchableText.includes(token)) ? 200 : 0;
}

export function RoleDropdownSelector({
  label = "Select Target Job Role:",
  selectedRole,
  onRoleChange,
  roles = ALL_JOB_ROLES,
  includeAllOption = false,
  allOptionLabel = "All Openings",
  className = "",
  helperText,
}: RoleDropdownSelectorProps) {
  const listboxId = useId();
  const rootRef = useRef<HTMLDivElement>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(-1);

  const roleOptions = useMemo<RoleOption[]>(() => {
    const uniqueRoles = new Map<string, RoleOption>();
    for (const item of roles) {
      const option = typeof item === "string" ? { role: item } : item;
      const key = option.role.trim().toLocaleLowerCase();
      if (key && !uniqueRoles.has(key)) uniqueRoles.set(key, option);
    }
    return [...uniqueRoles.values()];
  }, [roles]);

  const filteredRoles = useMemo(() => {
    return roleOptions
      .map((option) => ({ option, relevance: getRoleRelevance(option, searchQuery) }))
      .filter(({ relevance }) => relevance > 0)
      .sort((a, b) => b.relevance - a.relevance || a.option.role.localeCompare(b.option.role))
      .map(({ option }) => option);
  }, [roleOptions, searchQuery]);

  const selectedOption = roleOptions.find(
    (option) => option.role.toLocaleLowerCase() === selectedRole.toLocaleLowerCase(),
  );
  const isCustomRole = Boolean(selectedRole && selectedRole !== "ALL" && !selectedOption);
  const exactSearchMatch = roleOptions.some((option) =>
    [option.role, ...(option.aliases ?? [])].some(
      (name) => normalizeRole(name) === normalizeRole(searchQuery),
    ),
  );
  const showCustomOption = Boolean(searchQuery.trim()) && !exactSearchMatch;

  useEffect(() => {
    if (!isOpen) return;
    const handlePointerDown = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setIsOpen(false);
        setSearchQuery("");
      }
    };
    document.addEventListener("mousedown", handlePointerDown);
    return () => document.removeEventListener("mousedown", handlePointerDown);
  }, [isOpen]);

  const selectRole = (role: string) => {
    onRoleChange(role);
    setSearchQuery("");
    setIsOpen(false);
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Escape") {
      setIsOpen(false);
      setSearchQuery("");
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setIsOpen(true);
      const optionCount = filteredRoles.length + Number(showCustomOption);
      if (optionCount) {
        setActiveIndex((index) => (index + 1) % optionCount);
      }
      return;
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      const optionCount = filteredRoles.length + Number(showCustomOption);
      if (optionCount) {
        setActiveIndex((index) => (index <= 0 ? optionCount - 1 : index - 1));
      }
      return;
    }
    if (event.key === "Enter") {
      event.preventDefault();
      if (activeIndex < 0 && filteredRoles[0]) {
        selectRole(filteredRoles[0].role);
      } else if (activeIndex >= 0 && activeIndex < filteredRoles.length) {
        selectRole(filteredRoles[activeIndex].role);
      } else if (showCustomOption) {
        selectRole(searchQuery.trim());
      }
    }
  };

  return (
    <div className={`space-y-1.5 ${className}`} ref={rootRef}>
      <div className="flex h-[14px] items-center justify-between flex-wrap gap-2">
        <label className="flex items-center gap-1.5 text-[11px] font-semibold text-ink-600 dark:text-slate-300">
          <Target size={11} className="text-signal-600 shrink-0" />
          <span>{label}</span>
        </label>
        {isCustomRole && (
          <span className="text-[11px] font-semibold text-signal-700 bg-signal-500/10 px-2 py-0.5 rounded-md border border-signal-500/20">
            Custom Role
          </span>
        )}
      </div>

      <div className="relative">
        <Search size={14} className="pointer-events-none absolute left-3 top-[calc(50%+1px)] -translate-y-1/2 text-ink-400" />
        <input
          role="combobox"
          aria-label={label}
          aria-autocomplete="list"
          aria-expanded={isOpen}
          aria-controls={listboxId}
          aria-activedescendant={
            isOpen && activeIndex >= 0
              ? activeIndex < filteredRoles.length
                ? `${listboxId}-${activeIndex}`
                : `${listboxId}-custom`
              : undefined
          }
          value={isOpen ? searchQuery : selectedRole === "ALL" ? allOptionLabel : selectedRole}
          onFocus={() => {
            setSearchQuery("");
            setActiveIndex(-1);
            setIsOpen(true);
          }}
          onChange={(event) => {
            setSearchQuery(event.target.value);
            setActiveIndex(-1);
            setIsOpen(true);
          }}
          onKeyDown={handleKeyDown}
          placeholder={`Search ${roleOptions.length} roles or type a custom role…`}
          className="w-full rounded-lg border border-ink-200 bg-white py-2.5 pl-9 pr-9 text-sm font-semibold text-ink-900 outline-none shadow-2xs transition-all focus:border-signal-500 focus:ring-2 focus:ring-signal-500/10 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
        />
        <ChevronDown
          size={14}
          className={`absolute right-3 top-1/2 -translate-y-1/2 text-ink-400 pointer-events-none transition-transform ${isOpen ? "rotate-180" : ""}`}
        />

        {isOpen && (
          <div
            id={listboxId}
            role="listbox"
            aria-label="Matching career roles"
            className="absolute z-30 mt-1 w-full max-h-72 overflow-y-auto rounded-lg border border-ink-200 bg-white py-1 shadow-lg dark:border-slate-700 dark:bg-slate-900"
          >
            {includeAllOption && (
              <button
                type="button"
                role="option"
                id={`${listboxId}-all`}
                aria-selected={selectedRole === "ALL"}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => selectRole("ALL")}
                className={`w-full px-3 py-2 text-left text-xs font-semibold hover:bg-signal-500/10 dark:hover:bg-signal-950/50 ${selectedRole === "ALL" ? "bg-signal-500/10 text-signal-800 dark:text-signal-300" : "text-ink-800 dark:text-slate-200"}`}
              >
                {allOptionLabel}
              </button>
            )}

            {filteredRoles.map((option, index) => (
              <button
                type="button"
                role="option"
                id={`${listboxId}-${index}`}
                aria-selected={selectedRole.toLocaleLowerCase() === option.role.toLocaleLowerCase()}
                key={option.role}
                onMouseDown={(event) => event.preventDefault()}
                onMouseEnter={() => setActiveIndex(index)}
                onClick={() => selectRole(option.role)}
                className={`w-full px-3 py-2 text-left hover:bg-signal-500/10 dark:hover:bg-signal-950/50 ${activeIndex === index ? "bg-ink-50 dark:bg-slate-800" : ""}`}
              >
                <span className="block text-xs font-semibold text-ink-800 dark:text-slate-100">{option.role}</span>
                {(option.domain || option.subdomain) && (
                  <span className="block mt-0.5 text-[10px] text-ink-400 dark:text-slate-500">
                    {[option.domain, option.subdomain].filter(Boolean).join(" · ")}
                  </span>
                )}
              </button>
            ))}

            {showCustomOption && (
              <button
                type="button"
                role="option"
                aria-selected={false}
                id={`${listboxId}-custom`}
                onMouseDown={(event) => event.preventDefault()}
                onMouseEnter={() => setActiveIndex(filteredRoles.length)}
                onClick={() => selectRole(searchQuery.trim())}
                className={`w-full border-t border-ink-100 px-3 py-2.5 text-left text-xs font-semibold text-signal-700 hover:bg-signal-500/10 ${activeIndex === filteredRoles.length ? "bg-ink-50" : ""}`}
              >
                <span className="inline-flex items-center gap-1.5">
                  <PenLine size={12} />
                  Use “{searchQuery.trim()}” as a custom role
                </span>
              </button>
            )}

            {!filteredRoles.length && !showCustomOption && !includeAllOption && (
              <p className="px-3 py-3 text-xs text-ink-500 dark:text-slate-400">No roles found. Try another search.</p>
            )}
          </div>
        )}
      </div>

      {helperText && <p className="text-[11px] leading-relaxed text-ink-400 dark:text-slate-500">{helperText}</p>}
    </div>
  );
}
