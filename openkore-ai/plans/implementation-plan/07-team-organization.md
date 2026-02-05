# Team Organization and Roles

**Version:** 1.0  
**Date:** 2026-02-05  
**Status:** Planning Phase

---

## Table of Contents

1. [Overview](#1-overview)
2. [Team Structure](#2-team-structure)
3. [Role Definitions](#3-role-definitions)
4. [Responsibilities Matrix](#4-responsibilities-matrix)
5. [Communication Plan](#5-communication-plan)
6. [Skill Requirements](#6-skill-requirements)
7. [Onboarding Process](#7-onboarding-process)
8. [Knowledge Management](#8-knowledge-management)

---

## 1. Overview

### 1.1 Team Size

**Optimal Team:** 4-5 developers  
**Minimum Viable Team:** 3 developers  
**Peak Requirements:** 5 developers (Weeks 11-17)

### 1.2 Team Philosophy

- **Cross-functional**: Team members have overlapping skills
- **Collaborative**: Pair programming and code reviews
- **Self-organizing**: Team decides how to accomplish goals
- **Quality-focused**: Testing and documentation are core responsibilities

---

## 2. Team Structure

### 2.1 Organizational Chart

```mermaid
graph TD
    PM[Project Manager/Tech Lead]
    
    PM --> C++ Team[C++ Development Team]
    PM --> ML[ML/AI Engineer]
    PM --> Perl[Perl Developer]
    PM --> QA[QA Engineer]
    
    C++ Team --> Senior[Senior C++ Developer]
    C++ Team --> Mid[Mid-level C++ Developer]
    
    Senior -.Mentors.-> Mid
    ML -.Collaborates.-> Senior
    Perl -.Collaborates.-> Mid
```

### 2.2 Team Composition

| Role | Count | Required | Phase Focus |
|------|-------|----------|-------------|
| **Project Manager / Tech Lead** | 1 | Yes | All phases |
| **Senior C++ Developer** | 1 | Yes | Phases 1-2, 6-9 |
| **Mid-level C++ Developer** | 1-2 | Yes | Phases 1-2, 5, 8-9 |
| **ML/AI Engineer** | 1 | Yes | Phases 4, 7 |
| **Perl Developer** | 1 | Yes | Phases 1, 3, 5 |
| **QA Engineer** | 1 | Part-time | Phases 2+, full-time Phases 5-9 |
| **DevOps Engineer** | 1 | Part-time | Phases 0, 9 |

---

## 3. Role Definitions

### 3.1 Project Manager / Tech Lead

**Primary Responsibilities:**
- Overall project coordination
- Timeline and milestone management
- Risk management and mitigation
- Stakeholder communication
- Technical architecture decisions
- Code review oversight

**Key Activities:**
- Daily standups
- Weekly sprint planning
- Bi-weekly stakeholder updates
- Monthly risk reviews
- Architecture decision records
- Budget tracking

**Required Skills:**
- 5+ years software development
- Project management experience
- C++ and architecture knowledge
- Ragnarok Online game knowledge
- Leadership and communication

**Success Metrics:**
- Project delivered on time
- Budget maintained
- Quality targets met
- Team satisfaction high

---

### 3.2 Senior C++ Developer

**Primary Responsibilities:**
- Core engine architecture
- Performance-critical components (Reflex, IPC)
- Code quality and standards
- Mentoring junior developers
- Technical problem-solving

**Component Ownership:**
- IPC layer (Phase 1)
- Reflex Engine (Phase 2)
- Decision Coordinator (Phase 2)
- LLM Client (Phase 6)
- Performance optimization (Phase 9)

**Key Activities:**
- Implement core C++ components
- Performance profiling and optimization
- Code reviews
- Technical documentation
- Architecture refinement

**Required Skills:**
- Expert C++17/20
- High-performance computing
- Multi-threading and concurrency
- Memory management
- Debugging and profiling tools

**Success Metrics:**
- Performance targets met (< 1ms reflex)
- Zero critical bugs in owned components
- Code review quality
- Mentoring effectiveness

---

### 3.3 Mid-level C++ Developer

**Primary Responsibilities:**
- Rule Engine implementation
- Coordinator implementations
- Utility libraries
- Unit testing
- Integration support

**Component Ownership:**
- Rule Engine (Phase 2)
- Coordinators (Phase 5)
- Macro Generator (Phase 3)
- Configuration System
- Logging and utilities

**Key Activities:**
- Implement assigned components
- Write unit tests
- Bug fixing
- Documentation
- Code reviews (receiving and giving)

**Required Skills:**
- Proficient C++17/20
- Data structures and algorithms
- Testing frameworks (Google Test)
- CMake build system
- Version control (Git)

**Success Metrics:**
- Deliverables on time
- Test coverage > 80%
- Bug-free code
- Clean code reviews

---

### 3.4 ML/AI Engineer

**Primary Responsibilities:**
- ML pipeline design and implementation
- Model training and evaluation
- Feature engineering
- Online learning system
- Model deployment

**Component Ownership:**
- Training data collection (Phase 4)
- Feature extraction (Phase 4)
- Model training pipeline (Phase 4)
- Online learning (Phase 4)
- Model monitoring (Phase 7)

**Key Activities:**
- Design ML architecture
- Implement feature engineering
- Train and evaluate models
- Hyperparameter tuning
- ONNX export and deployment
- Performance monitoring

**Required Skills:**
- Machine learning (scikit-learn, XGBoost)
- Python programming
- Feature engineering
- Model evaluation and validation
- ONNX and model deployment
- Basic C++ (for integration)

**Success Metrics:**
- Model accuracy > 85% (Phase 4)
- Inference time < 100ms
- Cold-start strategy successful
- Online learning functional

---

### 3.5 Perl Developer

**Primary Responsibilities:**
- OpenKore plugin development
- IPC Perl client
- State capture implementation
- Action execution
- Macro hot-reload system

**Component Ownership:**
- aiCore plugin (Phase 1)
- State capture module (Phase 1)
- Action executor (Phase 1)
- Macro reloader (Phase 3)
- Plugin integration testing

**Key Activities:**
- Implement Perl plugin components
- OpenKore hook integration
- IPC client implementation
- Plugin testing
- Compatibility verification

**Required Skills:**
- Expert Perl programming
- OpenKore architecture knowledge
- Plugin development experience
- IPC/networking
- Ragnarok Online game knowledge

**Success Metrics:**
- Plugin compatibility 100%
- Zero plugin conflicts
- State capture accuracy 100%
- Action execution success > 95%

---

### 3.6 QA Engineer

**Primary Responsibilities:**
- Test strategy and planning
- Automated test development
- Manual testing
- Field testing coordination
- Bug tracking and reporting

**Activities:**
- Design test plans
- Implement integration tests
- Conduct field tests
- Performance testing
- Regression testing
- Bug verification
- Test automation

**Required Skills:**
- Test automation (Python, pytest)
- Performance testing
- Game testing experience
- Bug tracking tools
- Test framework knowledge

**Success Metrics:**
- Test coverage > 75%
- Critical bugs found before release
- Automated test suite functional
- Field test reports comprehensive

---

### 3.7 DevOps Engineer (Part-time)

**Primary Responsibilities:**
- CI/CD pipeline setup
- Build automation
- Deployment automation
- Infrastructure management

**Activities:**
- Setup GitHub Actions / Jenkins
- Configure build servers
- Create deployment scripts
- Monitor build health
- Optimize build times

**Required Skills:**
- CI/CD tools (GitHub Actions, Jenkins)
- Build systems (CMake, Make)
- Scripting (Bash, PowerShell, Python)
- Docker/containers

**Success Metrics:**
- CI/CD pipeline operational
- Build time < 10 minutes
- Zero deployment failures

---

## 4. Responsibilities Matrix

### 4.1 RACI Matrix

**Legend:**
- **R**: Responsible (does the work)
- **A**: Accountable (decision maker)
- **C**: Consulted (input sought)
- **I**: Informed (kept updated)

| Task | PM | Sr C++ | Mid C++ | ML Eng | Perl Dev | QA |
|------|----|----|----|----|----|----|
| **Architecture Design** | A | R | C | C | C | I |
| **IPC Implementation** | A | R | C | I | R | I |
| **Reflex Engine** | A | R | C | I | I | C |
| **Rule Engine** | A | C | R | I | I | C |
| **ML Pipeline** | A | C | I | R | I | C |
| **Coordinators** | A | C | R | I | I | C |
| **Perl Plugin** | A | C | C | I | R | C |
| **Macro System** | A | C | R | I | C | C |
| **LLM Integration** | A | R | C | C | C | I |
| **PDCA Loop** | A | C | C | R | I | C |
| **Testing Strategy** | A | C | C | I | C | R |
| **Performance Testing** | A | R | R | C | C | R |
| **Security Audit** | A | R | R | I | C | C |
| **Documentation** | A | C | C | C | C | C |
| **Release** | A | C | C | C | C | R |

### 4.2 Code Ownership

| Component | Primary Owner | Backup Owner |
|-----------|---------------|--------------|
| **IPC Layer** | Senior C++ | Perl Developer |
| **Reflex Engine** | Senior C++ | Mid C++ |
| **Rule Engine** | Mid C++ | Senior C++ |
| **ML Engine** | ML Engineer | Senior C++ |
| **Coordinators** | Mid C++ | Senior C++ |
| **Perl Plugin** | Perl Developer | Mid C++ |
| **Macro System** | Mid C++ | Perl Developer |
| **LLM Client** | Senior C++ | ML Engineer |
| **PDCA Loop** | ML Engineer | Senior C++ |
| **Testing** | QA Engineer | All |
| **Documentation** | All | PM |

---

## 5. Communication Plan

### 5.1 Meetings Schedule

**Daily Standup** (15 minutes)
- **When**: Every day, 9:00 AM
- **Who**: All team members
- **Format**:
  - What I did yesterday
  - What I'll do today
  - Blockers

**Sprint Planning** (2 hours)
- **When**: Monday, start of sprint
- **Who**: All team members
- **Agenda**:
  - Review sprint goals
  - Estimate tasks
  - Assign ownership
  - Identify dependencies

**Sprint Review** (1 hour)
- **When**: Friday, end of sprint
- **Who**: Team + stakeholders
- **Agenda**:
  - Demo completed work
  - Review metrics
  - Gather feedback

**Sprint Retrospective** (1 hour)
- **When**: Friday, after review
- **Who**: Team only
- **Agenda**:
  - What went well
  - What to improve
  - Action items

**Technical Design Review** (As needed)
- **When**: Before major component implementation
- **Who**: PM, relevant developers
- **Agenda**:
  - Review design proposal
  - Identify risks
  - Approve or request changes

**Weekly Stakeholder Update** (30 minutes)
- **When**: Friday afternoon
- **Who**: PM + stakeholders
- **Format**: Status report presentation

### 5.2 Communication Channels

| Channel | Purpose | Response Time |
|---------|---------|---------------|
| **Slack/Discord** | Daily communication | < 2 hours |
| **Email** | Formal communication | < 24 hours |
| **GitHub Issues** | Bug tracking, features | Per priority |
| **GitHub Discussions** | Design discussions | Asynchronous |
| **Video Calls** | Meetings, pairing | Scheduled |
| **Documentation** | Persistent knowledge | N/A |

### 5.3 Decision-Making Process

**Decision Types:**

**Architecture Decisions:**
- Proposed by: Any team member
- Reviewed by: Senior developers + PM
- Decided by: PM (with team consensus)
- Documented in: Architecture Decision Records (ADRs)

**Implementation Decisions:**
- Decided by: Component owner
- Reviewed by: At least one peer
- Documented in: Code comments, PR description

**Process Decisions:**
- Discussed in: Retrospectives
- Decided by: Team consensus
- Documented in: Team wiki

---

## 6. Skill Requirements

### 6.1 Required Skills Matrix

| Skill | PM | Sr C++ | Mid C++ | ML Eng | Perl Dev | QA |
|-------|----|----|----|----|----|----|
| **C++ (Expert)** | ○ | ● | ● | ○ | ○ | ○ |
| **C++ (Proficient)** | ● | ● | ● | ● | ○ | ● |
| **Python** | ○ | ○ | ○ | ● | ○ | ● |
| **Perl** | ○ | ○ | ○ | ○ | ● | ● |
| **Machine Learning** | ○ | ○ | ○ | ● | ○ | ○ |
| **System Architecture** | ● | ● | ○ | ○ | ○ | ○ |
| **Testing** | ○ | ● | ● | ● | ● | ● |
| **Git/Version Control** | ● | ● | ● | ● | ● | ● |
| **RO Game Knowledge** | ● | ○ | ○ | ○ | ● | ● |
| **OpenKore Knowledge** | ● | ○ | ○ | ○ | ● | ● |

**Legend:**
- ● Required
- ○ Nice to have
- (blank) Not needed

### 6.2 Skill Gaps and Training

**Identify Gaps:**
- Survey team skills at project start
- Identify critical gaps
- Plan training or hiring

**Training Plan:**
- C++20 features workshop (Week 1)
- OpenKore architecture overview (Week 1)
- ML fundamentals (for C++ developers, Week 11)
- ONNX Runtime usage (Week 15)

---

## 7. Onboarding Process

### 7.1 New Team Member Onboarding

**Week 1: Orientation**
- [ ] Welcome meeting with PM
- [ ] Access to repositories, tools, communication channels
- [ ] Review architecture documentation
- [ ] Setup development environment
- [ ] Build project from source
- [ ] Run all tests successfully

**Week 2: Learning**
- [ ] Shadow experienced team member
- [ ] Review existing codebase
- [ ] Attend all meetings
- [ ] Complete first small task (bug fix or test)
- [ ] First code review

**Week 3: Contributing**
- [ ] Assigned to component
- [ ] Implement first feature
- [ ] Write tests
- [ ] Participate in design discussions

**Week 4: Productive**
- [ ] Full velocity
- [ ] Independently contributing
- [ ] Reviewing others' code

### 7.2 Onboarding Checklist

```markdown
# New Team Member Checklist

## Access
- [ ] GitHub repository access
- [ ] Slack/Discord invite
- [ ] Email list added
- [ ] Documentation access
- [ ] Test server access (if applicable)

## Setup
- [ ] Development environment configured
- [ ] IDE installed and configured
- [ ] Project builds successfully
- [ ] Tests run successfully
- [ ] Can submit PR

## Knowledge
- [ ] Read architecture document
- [ ] Read technical specifications
- [ ] Understand IPC protocol
- [ ] Know testing strategy
- [ ] Familiar with coding standards

## Introduction
- [ ] Met all team members
- [ ] Understand team processes
- [ ] Know communication channels
- [ ] Understand decision-making process
```

---

## 8. Knowledge Management

### 8.1 Documentation Responsibility

| Document Type | Owner | Frequency |
|---------------|-------|-----------|
| **Architecture** | PM | As needed |
| **API Reference** | Component Owner | Per feature |
| **User Guide** | PM + QA | Per release |
| **Code Comments** | Developer | Per commit |
| **ADRs** | PM | Per decision |
| **Meeting Notes** | Rotating | Per meeting |
| **Release Notes** | PM | Per release |

### 8.2 Knowledge Sharing

**Practices:**
- Pair programming (2 hours/week minimum)
- Code reviews (all PRs)
- Tech talks (bi-weekly, rotating presenter)
- Documentation sprints (1 day/month)
- Knowledge transfer sessions (before departures)

**Documentation:**
```
docs/
├── architecture/
│   ├── decisions/           # ADRs
│   ├── diagrams/            # Architecture diagrams
│   └── specifications/      # Technical specs
├── development/
│   ├── setup-guide.md
│   ├── coding-standards.md
│   ├── testing-guide.md
│   └── troubleshooting.md
├── operations/
│   ├── deployment.md
│   ├── monitoring.md
│   └── incident-response.md
└── user/
    ├── user-guide.md
    ├── configuration.md
    └── faq.md
```

### 8.3 Code Review Process

**Review Requirements:**
- All PRs require 1+ approval
- Critical components require 2+ approvals
- Senior developer must approve architecture changes

**Review Checklist:**
- [ ] Code follows style guide
- [ ] Tests included and passing
- [ ] Documentation updated
- [ ] Performance acceptable
- [ ] No security issues
- [ ] Backwards compatible (if applicable)

**Review SLA:**
- Small PRs (< 100 lines): 24 hours
- Medium PRs (100-500 lines): 48 hours
- Large PRs (> 500 lines): 72 hours
- Critical fixes: 4 hours

---

## 9. Phase-Specific Team Configuration

### 9.1 Phase 0: Project Setup (Week 1)

**Team:** 2 developers + PM

| Role | Name | Responsibility |
|------|------|----------------|
| PM | TBD | Project setup, documentation |
| Senior C++ | TBD | Build system, C++ environment |
| Perl Developer | TBD | Perl environment, OpenKore setup |

### 9.2 Phase 1: Foundation (Weeks 2-4)

**Team:** 3 developers + PM

| Role | Responsibility |
|------|----------------|
| Senior C++ | IPC C++ implementation, engine core |
| Mid C++ | State management, configuration |
| Perl Developer | IPC Perl client, state capture, action executor |
| PM | Coordination, documentation |

**Parallel Work:**
- Senior C++: IPC server
- Perl Developer: IPC client
- Mid C++: State and configuration systems

### 9.3 Phase 2-3: Core Systems (Weeks 5-10)

**Team:** 3-4 developers + PM

**Phase 2 (Decision Engine):**
- Senior C++: Reflex Engine, Decision Coordinator
- Mid C++: Rule Engine
- Perl Developer: Integration support

**Phase 3 (Macro System) - Parallel:**
- Mid C++: Macro generator, template engine
- Perl Developer: Hot-reload system
- QA (part-time): Test macro scenarios

### 9.4 Phase 4-5: Intelligence Layer (Weeks 11-18)

**Team:** 5 developers + PM (Peak capacity)

**Phase 4 (ML Pipeline):**
- ML Engineer: Lead, model training
- Senior C++: ONNX integration
- Mid C++: Feature extraction

**Phase 5 (Coordinators) - Parallel:**
- Mid C++ #1: Combat, Consumables, Navigation
- Mid C++ #2: Economy, Progression, NPC
- Perl Developer: Testing support

**Phase 6 (LLM) - Sequential after 4:**
- Senior C++: LLM client
- Mid C++: Strategic planner
- ML Engineer: Prompt engineering

### 9.5 Phase 7-9: Advanced and Production (Weeks 19-29)

**Team:** 3-4 developers + PM + QA

**Phase 7 (PDCA):**
- ML Engineer: PDCA implementation
- Senior C++: Metrics system
- Mid C++: Strategy adjuster

**Phase 8 (Advanced Features):**
- Senior C++: Anti-detection
- Mid C++: Human mimicry
- Perl Developer: Stealth features

**Phase 9 (Hardening):**
- All team: Security, optimization, testing
- QA (full-time): Comprehensive testing
- PM: Documentation, release prep

---

## 10. Conflict Resolution

### 10.1 Technical Disagreements

**Process:**
1. Developers discuss directly
2. If unresolved → Tech Lead involvement
3. If still unresolved → Team vote
4. Final decision: PM/Tech Lead
5. Document decision in ADR

### 10.2 Resource Conflicts

**Process:**
1. Identify conflict early
2. Discuss in sprint planning
3. PM prioritizes
4. Adjust assignments if needed

### 10.3 Schedule Conflicts

**Process:**
1. Raise in standup immediately
2. Team discusses solutions
3. PM adjusts timeline if needed
4. Communicate changes to stakeholders

---

## 11. Performance Reviews

### 11.1 Individual Performance

**Review Frequency:** Monthly

**Criteria:**
- Deliverables completed on time
- Code quality (bugs, reviews)
- Test coverage
- Documentation quality
- Team collaboration
- Communication

**Format:**
- Self-assessment
- Peer feedback
- Manager assessment
- 1-on-1 discussion
- Growth plan

### 11.2 Team Performance

**Review Frequency:** After each phase

**Criteria:**
- Sprint velocity
- Quality metrics (bugs, coverage)
- Milestone achievement
- Stakeholder satisfaction
- Team morale

---

## 12. Succession Planning

### 12.1 Critical Roles

**Bus Factor Analysis:**
- Senior C++ Developer: Bus factor = 1 ⚠️
- ML Engineer: Bus factor = 1 ⚠️
- Perl Developer: Bus factor = 1 ⚠️

**Mitigation:**
- Cross-train Mid C++ developer on IPC and Reflex
- Document ML pipeline thoroughly
- Perl developer trains Mid C++ on OpenKore basics

### 12.2 Knowledge Transfer

**Required Documentation:**
- Component architecture diagrams
- Design decisions and rationale
- Critical algorithms explained
- Troubleshooting guides
- Testing procedures

**Practices:**
- Pair programming rotations
- Code review participation
- Technical presentations
- Shadowing critical tasks

---

## Team Culture

### Values

- **Quality First**: Never compromise on code quality
- **Collaboration**: Help each other succeed
- **Transparency**: Open communication about issues
- **Continuous Learning**: Always improving skills
- **User Focus**: Build what users need

### Working Principles

- Code reviews are learning opportunities, not criticism
- Ask questions early and often
- Document decisions and rationale
- Test thoroughly before committing
- Refactor when needed
- Celebrate successes together

---

**Next Document:** [Comprehensive Implementation Plan](00-IMPLEMENTATION-PLAN.md)
