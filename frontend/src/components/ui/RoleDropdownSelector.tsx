import React, { useState, useEffect } from "react";
import { Target, PenLine } from "lucide-react";
import { ALL_JOB_ROLES } from "../../lib/roleConstants";

interface RoleDropdownSelectorProps {
  label?: string;
  selectedRole: string; // The active effective role string ("ALL", "Backend Developer", or custom)
  onRoleChange: (newRole: string) => void;
  roles?: string[]; // Predefined roles list
  includeAllOption?: boolean; // Whether to include "All Openings"
  allOptionLabel?: string;
  className?: string;
  helperText?: string;
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
  const isPredefined = includeAllOption
    ? selectedRole === "ALL" || roles.includes(selectedRole)
    : roles.includes(selectedRole);

  const [dropdownSelection, setDropdownSelection] = useState<string>(() => {
    if (includeAllOption && (selectedRole === "ALL" || !selectedRole)) return "ALL";
    if (roles.includes(selectedRole)) return selectedRole;
    return "OTHER";
  });

  const [customRoleText, setCustomRoleText] = useState<string>(() => {
    if (!isPredefined && selectedRole !== "ALL") return selectedRole;
    return "";
  });

  // Keep internal state synchronized if external selectedRole changes
  useEffect(() => {
    if (includeAllOption && selectedRole === "ALL") {
      setDropdownSelection("ALL");
      setCustomRoleText("");
    } else if (roles.includes(selectedRole)) {
      setDropdownSelection(selectedRole);
      setCustomRoleText("");
    } else if (selectedRole) {
      setDropdownSelection("OTHER");
      setCustomRoleText(selectedRole);
    }
  }, [selectedRole, roles, includeAllOption]);

  // Debounce custom-role input to avoid sending API queries on every keystroke
  useEffect(() => {
    if (dropdownSelection !== "OTHER") return;
    const timer = setTimeout(() => {
      onRoleChange(customRoleText);
    }, 350);
    return () => clearTimeout(timer);
  }, [customRoleText, dropdownSelection]);

  const handleDropdownChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newVal = e.target.value;
    setDropdownSelection(newVal);

    if (newVal === "ALL") {
      setCustomRoleText("");
      onRoleChange("ALL");
    } else if (newVal === "OTHER") {
      onRoleChange(customRoleText || "");
    } else {
      setCustomRoleText("");
      onRoleChange(newVal);
    }
  };

  const handleCustomTextChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setCustomRoleText(e.target.value);
  };

  const isOtherActive = dropdownSelection === "OTHER";

  return (
    <div className={`space-y-2.5 ${className}`}>
      <div className="flex items-center justify-between flex-wrap gap-2">
        <label className="text-xs font-bold uppercase tracking-wider text-ink-700 flex items-center gap-1.5">
          <Target size={13} className="text-signal-600 shrink-0" />
          <span>{label}</span>
        </label>
        {isOtherActive && (
          <span className="text-[11px] font-semibold text-signal-700 bg-signal-500/10 px-2 py-0.5 rounded-md border border-signal-500/20">
            Custom Role Mode
          </span>
        )}
      </div>

      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5">
        {/* Role Dropdown Select */}
        <div className="relative flex-1">
          <select
            value={dropdownSelection}
            onChange={handleDropdownChange}
            className="w-full px-3.5 py-2 rounded-lg border border-ink-200 bg-white text-xs font-semibold text-ink-900 outline-none focus:border-signal-500 focus:ring-2 focus:ring-signal-500/10 transition-all shadow-2xs cursor-pointer appearance-none pr-8"
          >
            {includeAllOption && (
              <option value="ALL" className="font-semibold text-ink-900">
                {allOptionLabel}
              </option>
            )}

            <optgroup label="Standard Tech & Engineering Roles">
              {roles.map((r) => (
                <option key={r} value={r} className="text-ink-800">
                  {r}
                </option>
              ))}
            </optgroup>

            <option value="OTHER" className="font-bold text-signal-700">
              ✍️ Other (Specify Custom Role)…
            </option>
          </select>

          {/* Custom Chevron Indicator */}
          <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2.5 text-ink-500">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </div>

        {/* Custom Role Text Input when "Other" is selected */}
        {isOtherActive && (
          <div className="relative flex-1 animate-in fade-in slide-in-from-top-1 duration-200">
            <PenLine size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-signal-600" />
            <input
              type="text"
              autoFocus
              value={customRoleText}
              onChange={handleCustomTextChange}
              placeholder="Write your custom job role (e.g. Rust Systems Engineer)…"
              className="w-full pl-8 pr-3 py-2 rounded-lg border border-signal-300 bg-signal-50/40 text-xs font-medium text-ink-900 outline-none focus:border-signal-600 focus:ring-2 focus:ring-signal-500/15 shadow-2xs placeholder:text-ink-400"
            />
          </div>
        )}
      </div>

      {helperText && <p className="text-[11px] text-ink-400 leading-relaxed">{helperText}</p>}
    </div>
  );
}
