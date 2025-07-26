import React from 'react';
import { Globe } from 'lucide-react';

interface EventDropdownProps {
  value: string; // Changed to non-optional
  onValueChange: (value: string) => void;
  disabled?: boolean;
  options: { value: string; label: string; disabled?: boolean }[]; // Added options prop
  placeholder?: string; // Added placeholder prop
}

const EventDropdown: React.FC<EventDropdownProps> = ({
  value,
  onValueChange,
  disabled = false,
  options, // Destructure options
  placeholder, // Destructure placeholder
}) => {
  return (
    <div className="space-y-2">
      <label htmlFor="event-select" className="text-sm font-semibold text-white flex items-center gap-2">
        <Globe className="w-4 h-4 text-cyan-400" />
        Event Type
      </label>
      <select
        id="event-select"
        value={value}
        onChange={(e) => onValueChange(e.target.value)}
        disabled={disabled}
        className="w-full p-3 bg-black/40 border border-cyan-500/30 rounded-lg text-white focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/20 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {placeholder && <option value="" className="bg-[--background-secondary] text-gray-400">{placeholder}</option>}
        {options.map((option) => (
          <option
            key={option.value}
            value={option.value}
            disabled={option.disabled}
            className="bg-[--background-secondary] text-[--primary-text]"
          >
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
};

export default EventDropdown;
