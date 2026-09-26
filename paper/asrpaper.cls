\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{asrpaper}[2026/09/02 ASR Institutional Paper Standard v3.0]
\LoadClass[10pt,a4paper]{article}
\RequirePackage[T1]{fontenc}
\RequirePackage{lmodern}
\RequirePackage{microtype}
\RequirePackage{geometry}
\geometry{top=17mm,bottom=18mm,left=17mm,right=17mm,columnsep=7.2mm}
\RequirePackage{xcolor}
\RequirePackage{graphicx}
\RequirePackage{booktabs}
\RequirePackage{tabularx}
\RequirePackage{array}
\RequirePackage{amsmath,amssymb,mathtools}
\RequirePackage{enumitem}
\RequirePackage{titlesec}
\RequirePackage{fancyhdr}
\RequirePackage{hyperref}
\RequirePackage{caption}
\RequirePackage{etoolbox}
\RequirePackage{lastpage}
\RequirePackage{balance}
\RequirePackage{ragged2e}
\RequirePackage{listings}
\RequirePackage{tikz}
\RequirePackage{multicol}

\definecolor{ASRBlack}{HTML}{111118}
\definecolor{ASRPurple}{HTML}{6C3DD2}
\definecolor{ASRPurpleSoft}{HTML}{8B5CF6}
\definecolor{ASRLight}{HTML}{F4F1FA}
\definecolor{ASRRule}{HTML}{DED9E8}
\definecolor{ASRText}{HTML}{1C1B20}
\definecolor{ASRMuted}{HTML}{6B6873}
\definecolor{ASRCode}{HTML}{F3F1F6}

\color{ASRText}
\hypersetup{colorlinks=true,linkcolor=ASRPurple,citecolor=ASRPurple,urlcolor=ASRPurple,pdfborder={0 0 0}}
\setlength{\parindent}{0pt}
\setlength{\parskip}{3.1pt}
\setlist[itemize]{leftmargin=*,itemsep=2pt,topsep=3pt}
\setlist[enumerate]{leftmargin=*,itemsep=2pt,topsep=3pt}
\captionsetup{font=small,labelfont={bf,color=ASRBlack},textfont={color=ASRText},skip=4pt}
\setlength{\columnseprule}{0pt}
\setlength{\columnsep}{7.2mm}

\titleformat{\section}{\large\bfseries\color{ASRBlack}}{\textcolor{ASRPurple}{\thesection}}{0.6em}{}
\titlespacing*{\section}{0pt}{9pt}{4pt}
\titleformat{\subsection}{\normalsize\bfseries\color{ASRBlack}}{\textcolor{ASRPurple}{\thesubsection}}{0.55em}{}
\titlespacing*{\subsection}{0pt}{6pt}{2pt}

% Metadata
\newcommand{\ASRDocumentTypeValue}{Research Paper}
\newcommand{\ASRDocumentIDValue}{ASR-RP-YYYY-XXX}
\newcommand{\ASRVersionValue}{1.0}
\newcommand{\ASRStatusValue}{Working Draft}
\newcommand{\ASRTeamValue}{ASR Research}
\newcommand{\ASRDomainValue}{Quantitative Finance}
\newcommand{\ASRDateValue}{Month YYYY}
\newcommand{\ASRSubtitleValue}{Optional subtitle describing the empirical, mathematical or model scope}
\newcommand{\ASRKeywordsValue}{quantitative research; stochastic modelling; financial markets; scientific computing}
\newcommand{\ASRClassificationValue}{Optional: JEL / internal taxonomy / model-evaluation domain}
\newcommand{\ASRShortTitleValue}{Short Paper Title}
\newcommand{\ASREmailValue}{research@asr-lab.online}
\newcommand{\ASRRepositoryValue}{Not assigned}
\newcommand{\ASRDOIValue}{Not assigned}
\newcommand{\ASRReproStatusValue}{Pending}
\newcommand{\ASRHeadResearchValue}{}
\newcommand{\ASRHeadAnalystValue}{}
\newcommand{\ASRHeadIndustryValue}{}
\newcommand{\ASRApprovalStatusValue}{Pending final approval}
\newcommand{\ASRApprovalDateValue}{Not assigned}
\newcommand{\ASRDocumentType}[1]{\renewcommand{\ASRDocumentTypeValue}{#1}}
\newcommand{\ASRDocumentID}[1]{\renewcommand{\ASRDocumentIDValue}{#1}}
\newcommand{\ASRVersion}[1]{\renewcommand{\ASRVersionValue}{#1}}
\newcommand{\ASRStatus}[1]{\renewcommand{\ASRStatusValue}{#1}}
\newcommand{\ASRTeam}[1]{\renewcommand{\ASRTeamValue}{#1}}
\newcommand{\ASRDomain}[1]{\renewcommand{\ASRDomainValue}{#1}}
\newcommand{\ASRPublicationDate}[1]{\renewcommand{\ASRDateValue}{#1}}
\newcommand{\ASRSubtitle}[1]{\renewcommand{\ASRSubtitleValue}{#1}}
\newcommand{\ASRKeywords}[1]{\renewcommand{\ASRKeywordsValue}{#1}}
\newcommand{\ASRClassification}[1]{\renewcommand{\ASRClassificationValue}{#1}}
\newcommand{\ASRShortTitle}[1]{\renewcommand{\ASRShortTitleValue}{#1}}
\newcommand{\ASREmail}[1]{\renewcommand{\ASREmailValue}{#1}}
\newcommand{\ASRRepository}[1]{\renewcommand{\ASRRepositoryValue}{#1}}
\newcommand{\ASRDOI}[1]{\renewcommand{\ASRDOIValue}{#1}}
\newcommand{\ASRReproStatus}[1]{\renewcommand{\ASRReproStatusValue}{#1}}
\newcommand{\ASRHeadResearch}[1]{\renewcommand{\ASRHeadResearchValue}{#1}}
\newcommand{\ASRHeadAnalyst}[1]{\renewcommand{\ASRHeadAnalystValue}{#1}}
\newcommand{\ASRHeadIndustry}[1]{\renewcommand{\ASRHeadIndustryValue}{#1}}
\newcommand{\ASRApprovalStatus}[1]{\renewcommand{\ASRApprovalStatusValue}{#1}}
\newcommand{\ASRApprovalDate}[1]{\renewcommand{\ASRApprovalDateValue}{#1}}

\pagestyle{fancy}
\fancyhf{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}
\fancyhead[L]{\scriptsize\bfseries\color{ASRBlack}ASR}
\fancyhead[R]{\scriptsize\color{ASRMuted}\ASRShortTitleValue}
\fancyfoot[L]{\scriptsize\color{ASRMuted}Alpha Stochastic Research}
\fancyfoot[R]{\scriptsize\color{ASRMuted}\thepage}

\lstset{basicstyle=\ttfamily\scriptsize,backgroundcolor=\color{ASRCode},frame=none,breaklines=true,xleftmargin=4pt,xrightmargin=4pt,aboveskip=4pt,belowskip=4pt}

\makeatletter
\newcommand{\ASRMakeTitle}{%
  \thispagestyle{empty}%
  \noindent
  \begin{minipage}[t]{0.70\textwidth}
    \vspace{0pt}\includegraphics[height=19mm]{asr_mark_light.png}\hspace{5mm}%
    \begin{minipage}[b]{0.60\textwidth}
      {\fontsize{16}{17}\selectfont\bfseries\color{ASRBlack}ALPHA \textcolor{ASRPurple}{STOCHASTIC} RESEARCH}\par
      \vspace{2pt}{\scriptsize\color{ASRMuted}\textls[145]{INDEPENDENT QUANTITATIVE RESEARCH LAB}}
    \end{minipage}
  \end{minipage}%
  \begin{minipage}[t]{0.30\textwidth}\vspace{1pt}\raggedleft
    {\small\color{ASRMuted}\ASRDateValue}\\[-1pt]
    {\small\color{ASRMuted}Version \ASRVersionValue}
  \end{minipage}
  \vspace{8pt}
  {\color{ASRPurple}\rule{\textwidth}{0.8pt}}\par
  \vspace{22mm}
  {\raggedright\fontsize{26}{29}\selectfont\bfseries\color{ASRBlack}\@title\par}
  \vspace{6pt}
  {\fontsize{12}{15}\selectfont\color{ASRMuted}\ASRSubtitleValue\par}
  \vspace{13mm}
  {\large\bfseries\color{ASRBlack}\@author\par}
  \vspace{4pt}
  {\small\color{ASRMuted}\ASRTeamValue\par}
  {\small\color{ASRMuted}\ASREmailValue\par}
  \vspace{15mm}
  \noindent\colorbox{ASRLight}{\parbox{\dimexpr\textwidth-2\fboxsep\relax}{\vspace{7pt}{\small\bfseries\color{ASRPurple}ABSTRACT}\par\vspace{5pt}{\small\@abstract}\vspace{7pt}}}
  \par\vspace{8mm}
  {\small\textbf{\textcolor{ASRPurple}{Keywords}}\quad \ASRKeywordsValue\par}
  \vspace{4pt}
  {\small\textbf{\textcolor{ASRPurple}{Classification}}\quad \ASRClassificationValue\par}
  \vfill
  {\scriptsize\color{ASRMuted}Alpha Stochastic Research is an independent quantitative research lab focused on reproducible research, stochastic modelling, data analysis and scientific computing.}\par
  \newpage\twocolumn
}
\newcommand{\ASRabstract}[1]{\def\@abstract{#1}}
\def\@abstract{Write a compact abstract of approximately 150--220 words. State the problem, method, principal result and scientific implication.}
\makeatother

\newenvironment{asrstandard}{\par\medskip\noindent\begin{minipage}{\columnwidth}\small\color{ASRText}\textcolor{ASRPurple}{\rule{\columnwidth}{1.2pt}}\par\vspace{3pt}}{\vspace{3pt}\textcolor{ASRRule}{\rule{\columnwidth}{0.4pt}}\end{minipage}\par\medskip}

\newenvironment{asrclaim}[2][]{\par\medskip\noindent\begin{minipage}{\columnwidth}\small\textcolor{ASRPurple}{\rule{\columnwidth}{1.2pt}}\par\vspace{3pt}{\bfseries\color{ASRPurple}CLAIM #2}\ifstrempty{#1}{}{\hfill{\scriptsize\bfseries\color{ASRMuted}#1}}\par\vspace{2pt}\color{ASRText}}{\vspace{3pt}\textcolor{ASRRule}{\rule{\columnwidth}{0.4pt}}\end{minipage}\par\medskip}

\newcommand{\ASRBlockHeading}[1]{\par\vspace{7pt}{\normalsize\bfseries\color{ASRBlack}#1}\par\vspace{2pt}{\color{ASRRule}\rule{\columnwidth}{0.4pt}}\vspace{3pt}}
\newenvironment{asrrepro}{\small\begin{tabular}{@{}>{\bfseries\color{ASRBlack}}p{0.31\columnwidth} p{0.61\columnwidth}@{}}}{\end{tabular}}
\newcommand{\ASRMetadataBlock}{\ASRBlockHeading{Publication metadata}{\small\textbf{Document ID:} \ASRDocumentIDValue\par\textbf{Version:} \ASRVersionValue\par\textbf{Repository:} \ASRRepositoryValue\par\textbf{DOI:} \ASRDOIValue\par}}
\newcommand{\ASRLeadershipApproval}{\ASRBlockHeading{Scientific leadership approval}\small\ifdefempty{\ASRHeadResearchValue}{}{\textbf{Head of Research:} \ASRHeadResearchValue\par}\ifdefempty{\ASRHeadAnalystValue}{}{\textbf{Head of Analyst:} \ASRHeadAnalystValue\par}\ifdefempty{\ASRHeadIndustryValue}{}{\textbf{Head of Industry:} \ASRHeadIndustryValue\par}\textbf{Status:} \ASRApprovalStatusValue\par\textbf{Date:} \ASRApprovalDateValue\par}
\endinput
