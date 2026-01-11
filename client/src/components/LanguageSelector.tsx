import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Globe } from "lucide-react";

const languages = [
  { code: "en", name: "English" },
  { code: "ar", name: "العربية (Arabic)" },
];

interface LanguageSelectorProps {
  value: string;
  onChange: (value: string) => void;
}

export function LanguageSelector({ value, onChange }: LanguageSelectorProps) {
  const selectedLang = languages.find((l) => l.code === value);

  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger
        className="w-[140px] gap-2"
        data-testid="select-language"
      >
        <Globe className="h-4 w-4 text-muted-foreground" />
        <SelectValue placeholder="Language">
          {selectedLang?.name || "Language"}
        </SelectValue>
      </SelectTrigger>
      <SelectContent>
        {languages.map((lang) => (
          <SelectItem
            key={lang.code}
            value={lang.code}
            data-testid={`select-language-${lang.code}`}
          >
            <span className="flex items-center gap-2">
              <span className="text-xs font-medium text-muted-foreground uppercase w-6">
                {lang.code}
              </span>
              <span>{lang.name}</span>
            </span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

export { languages };
