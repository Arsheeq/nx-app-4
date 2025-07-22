import React from "react";
import { useStore } from "@/lib/store";
import { Card } from "@/components/ui/card";
import { Calendar, CalendarDays } from "lucide-react";

export function FrequencySelection() {
  const { frequency, setFrequency } = useStore();

  const frequencyOptions = [
    {
      id: "daily",
      title: "Daily",
      description: "Last 24 hours",
      icon: Calendar,
    },
    {
      id: "weekly",
      title: "Weekly", 
      description: "Last 7 days",
      icon: CalendarDays,
    },
  ];

  return (
    <section>
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold bg-gradient-to-r from-[#3DB3E3] via-[#6866C1] to-[#E865A0] bg-clip-text text-transparent inline-block">
          Select Time Period
        </h2>
        <p className="text-gray-500 mt-2">
          Choose the time period for your utilization report
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-2xl mx-auto">
        {frequencyOptions.map((option) => {
          const Icon = option.icon;
          const isSelected = frequency === option.id;

          return (
            <Card
              key={option.id}
              className={`p-6 cursor-pointer transition-all duration-200 hover:shadow-lg ${
                isSelected
                  ? "border-2 border-purple-500 bg-purple-50"
                  : "border border-gray-200 hover:border-purple-300"
              }`}
              onClick={() => setFrequency(option.id as "daily" | "weekly")}
            >
              <div className="text-center">
                <div className="flex justify-center mb-4">
                  <Icon 
                    className={`h-12 w-12 ${
                      isSelected ? "text-purple-600" : "text-gray-400"
                    }`}
                  />
                </div>
                <h3 className="text-xl font-semibold mb-2">{option.title}</h3>
                <p className="text-gray-500">{option.description}</p>

                {isSelected && (
                  <div className="mt-4 flex justify-center">
                    <div className="w-6 h-6 bg-purple-600 rounded-full flex items-center justify-center">
                      <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                    </div>
                  </div>
                )}
              </div>
            </Card>
          );
        })}
      </div>
    </section>
  );
}