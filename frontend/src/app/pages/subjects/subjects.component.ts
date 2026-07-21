import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

interface Subject {
  id: string;
  name: string;
  icon: string;
  color: string;
  description: string;
  topics: string[];
  questionCount: number;
  difficulty: string;
}

@Component({
  selector: 'app-subjects',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './subjects.component.html',
  styleUrls: ['./subjects.component.css']
})
export class SubjectsComponent {
  activeFilter = signal('All');
  searchQuery = signal('');
  difficulties = ['All', 'Easy', 'Medium', 'Hard'];

  allSubjects: Subject[] = [
    {
      id: 'mathematics',
      name: 'Mathematics',
      icon: '🔢',
      color: '#7c3aed',
      description: 'From basic arithmetic to advanced calculus and statistics',
      topics: ['Algebra', 'Calculus', 'Statistics', 'Geometry', 'Trigonometry', 'Linear Algebra'],
      questionCount: 1240,
      difficulty: 'Medium',
    },
    {
      id: 'physics',
      name: 'Physics',
      icon: '⚡',
      color: '#3b82f6',
      description: 'Laws of nature: mechanics, waves, electricity, and quantum physics',
      topics: ['Mechanics', 'Electromagnetism', 'Thermodynamics', 'Optics', 'Quantum'],
      questionCount: 890,
      difficulty: 'Hard',
    },
    {
      id: 'chemistry',
      name: 'Chemistry',
      icon: '🧪',
      color: '#10b981',
      description: 'Elements, reactions, molecular structures, and chemical processes',
      topics: ['Organic Chemistry', 'Inorganic', 'Physical Chemistry', 'Electrochemistry'],
      questionCount: 750,
      difficulty: 'Hard',
    },
    {
      id: 'biology',
      name: 'Biology',
      icon: '🧬',
      color: '#06b6d4',
      description: 'The study of life: from cells to ecosystems',
      topics: ['Cell Biology', 'Genetics', 'Evolution', 'Ecology', 'Human Biology'],
      questionCount: 680,
      difficulty: 'Medium',
    },
    {
      id: 'history',
      name: 'History',
      icon: '📜',
      color: '#f59e0b',
      description: 'World history from ancient civilizations to modern times',
      topics: ['Ancient World', 'Middle Ages', 'Modern History', 'World Wars', 'Cold War'],
      questionCount: 520,
      difficulty: 'Easy',
    },
    {
      id: 'geography',
      name: 'Geography',
      icon: '🌍',
      color: '#f97316',
      description: 'Physical and human geography, maps, and environmental systems',
      topics: ['Physical Geography', 'Human Geography', 'Cartography', 'Climate'],
      questionCount: 430,
      difficulty: 'Easy',
    },
    {
      id: 'computer-science',
      name: 'Computer Science',
      icon: '💻',
      color: '#8b5cf6',
      description: 'Programming, algorithms, data structures, and AI',
      topics: ['Python', 'Data Structures', 'Algorithms', 'AI & ML', 'Databases', 'Web Dev'],
      questionCount: 1050,
      difficulty: 'Hard',
    },
    {
      id: 'literature',
      name: 'Literature',
      icon: '📖',
      color: '#ec4899',
      description: 'Poetry, prose, analysis, and creative writing',
      topics: ['Poetry Analysis', 'Fiction', 'Shakespeare', 'Essay Writing', 'Drama'],
      questionCount: 380,
      difficulty: 'Easy',
    },
    {
      id: 'economics',
      name: 'Economics',
      icon: '💹',
      color: '#14b8a6',
      description: 'Micro and macroeconomics, markets, and financial systems',
      topics: ['Microeconomics', 'Macroeconomics', 'Trade', 'Finance', 'Behavioral Economics'],
      questionCount: 490,
      difficulty: 'Medium',
    },
  ];

  filteredSubjects = signal<Subject[]>(this.allSubjects);

  onSearch(e: Event): void {
    const query = (e.target as HTMLInputElement).value.toLowerCase();
    this.searchQuery.set(query);
    this.applyFilters();
  }

  applyFilters(): void {
    let filtered = this.allSubjects;
    const filter = this.activeFilter();
    const query = this.searchQuery();

    if (filter !== 'All') {
      filtered = filtered.filter(s => s.difficulty === filter);
    }
    if (query) {
      filtered = filtered.filter(s =>
        s.name.toLowerCase().includes(query) ||
        s.description.toLowerCase().includes(query) ||
        s.topics.some(t => t.toLowerCase().includes(query))
      );
    }
    this.filteredSubjects.set(filtered);
  }
}
