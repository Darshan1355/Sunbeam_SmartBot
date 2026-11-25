import React from 'react';
import { BookOpen, GitCompare, Briefcase, GraduationCap, FileText, Sparkles } from 'lucide-react';

interface WelcomeScreenProps {
  onSelectPrompt: (prompt: string) => void;
}

export const WelcomeScreen: React.FC<WelcomeScreenProps> = ({ onSelectPrompt }) => {
  const suggestions = [
    {
      title: 'Explore Sunbeam courses',
      desc: 'Schedules, duration, fees, and syllabus for modular courses.',
      icon: BookOpen,
      prompt: 'What courses does Sunbeam offer and what are their fees?',
      gradient: 'from-orange-500/10 to-amber-500/10 border-orange-500/20 text-orange-400',
    },
    {
      title: 'Compare two courses',
      desc: 'Compare Core Java and C++ side-by-side.',
      icon: GitCompare,
      prompt: 'Compare Core Java and C++ courses in terms of duration and fees.',
      gradient: 'from-blue-500/10 to-cyan-500/10 border-blue-500/20 text-blue-400',
    },
    {
      title: 'Find internship opportunities',
      desc: 'Generative AI, Android, Web Development, and Cyber Security batches.',
      icon: Briefcase,
      prompt: 'What internship batches are currently available at Sunbeam?',
      gradient: 'from-emerald-500/10 to-teal-500/10 border-emerald-500/20 text-emerald-400',
    },
    {
      title: 'Explain course eligibility',
      desc: 'Prerequisites and target audience for specialized modules.',
      icon: GraduationCap,
      prompt: 'What are the eligibility requirements and prerequisites for Apache Spark Mastery?',
      gradient: 'from-purple-500/10 to-indigo-500/10 border-purple-500/20 text-purple-400',
    },
    {
      title: 'Summarize training programs',
      desc: 'Institutional overview, campus facilities, and industrial training format.',
      icon: FileText,
      prompt: 'Summarize Sunbeam industrial training and the Hinjawadi campus infrastructure.',
      gradient: 'from-rose-500/10 to-pink-500/10 border-rose-500/20 text-rose-400',
    },
  ];

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-6 text-center max-w-3xl mx-auto">
      <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-orange-600 via-orange-500 to-amber-400 flex items-center justify-center shadow-2xl shadow-orange-500/30 text-white mb-6 animate-pulse">
        <Sparkles className="w-8 h-8" />
      </div>

      <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-100 tracking-tight mb-3">
        Welcome to <span className="bg-gradient-to-r from-orange-400 to-amber-300 bg-clip-text text-transparent">Sunbeam SmartBot</span>
      </h1>

      <p className="text-sm sm:text-base text-slate-400 max-w-xl mb-10 leading-relaxed">
        Your intelligent AI assistant for courses, internships, training and career guidance.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 w-full text-left">
        {suggestions.map((item, index) => {
          const Icon = item.icon;
          return (
            <button
              key={index}
              onClick={() => onSelectPrompt(item.prompt)}
              className={`p-4 rounded-2xl bg-slate-900/60 hover:bg-slate-900 border transition-all duration-200 hover:shadow-lg hover:-translate-y-0.5 group flex flex-col justify-between ${item.gradient}`}
            >
              <div className="flex items-center gap-3 mb-2">
                <div className="p-2 rounded-xl bg-slate-800/80 group-hover:scale-110 transition-transform">
                  <Icon className="w-5 h-5" />
                </div>
                <h3 className="text-sm font-semibold text-slate-200 group-hover:text-white transition-colors">
                  {item.title}
                </h3>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                {item.desc}
              </p>
            </button>
          );
        })}
      </div>
    </div>
  );
};
