# What are ADRs?

Architectural Decision Records (ADR's) provide a lightweight format for documenting the reasons why certain architectural or technical decisions were taken, and more importantly the _context_ which led to these decisions. This allows to revisit these decisions later on, in case the context changes or more information becomes available. See Michael Nygard's [blog post](http://thinkrelevance.com/blog/2011/11/15/documenting-architecture-decisions) for more details on ADR's.

Despite the name "architectural decision records", where appropriate it is also encouraged to document technological decisions (for example which Javascript framework to use for a web frontend) or "cultural" decisions.

ADR's should be placed in sepearate files that are numbered sequentially (e.g. `0001-some-useful-description.md`). The contents should follow this [template](https://github.com/joelparkerhenderson/architecture_decision_record/blob/master/adr_template_by_michael_nygard.md):

- **Title:** short present tense imperative phrase, less than 50 characters, like a git commit message.

- **Date:** when was this issue discussed (to give approximate temporal context)

- **Status:** proposed, accepted, rejected, deprecated, superseded, etc.

- **Context:** what is the issue that we're seeing that is motivating this decision or change.
  This section describes the forces at play, including technological, political, social, and project local. These forces are probably in tension, and should be called out as such. The language in this section is value-neutral. It is simply describing facts.

- **Decision:** what is the change that we're actually proposing or doing (describes our response to these forces)

- **Consequences:** what becomes easier or more difficult to do because of this change.
  All consequences should be listed here, not just the "positive" ones. A particular decision may have positive, negative, and neutral consequences, but all of them affect the team and project in the future.
