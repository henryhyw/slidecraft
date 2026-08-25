# Security Policy

Report vulnerabilities privately to the repository maintainers before public disclosure.

Slidecraft treats uploaded documents, images, SVGs, model outputs, component packages, and provider responses as untrusted input. Provider credentials are read from named environment variables. They must not be written into run artifacts. Local component directories cannot execute Python unless the user explicitly installs a trusted component-factory package.

Normal pipeline runs are non-interactive. PowerPoint automation and model downloads require explicit setup commands. The framework does not attempt to grant operating-system permissions automatically.
