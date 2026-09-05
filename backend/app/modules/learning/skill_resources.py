"""
Curated, high-quality free learning resources per technical skill.
Includes official documentation, tutorials, interactive sandboxes, and video courses.
"""

SKILL_RESOURCES: dict[str, list[str]] = {
    # Programming Languages
    "python": [
        "https://docs.python.org/3/tutorial/",
        "https://www.freecodecamp.org/learn/scientific-computing-with-python/",
        "https://realpython.com/",
    ],
    "javascript": [
        "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide",
        "https://javascript.info/",
        "https://www.freecodecamp.org/learn/javascript-algorithms-and-data-structures-v8/",
    ],
    "typescript": [
        "https://www.typescriptlang.org/docs/handbook/intro.html",
        "https://www.totaltypescript.com/tutorials",
    ],
    "java": [
        "https://dev.java/learn/",
        "https://www.baeldung.com/get-started-with-java-series",
        "https://www.codecademy.com/learn/learn-java",
    ],
    "c++": [
        "https://en.cppreference.com/w/",
        "https://www.learncpp.com/",
    ],
    "c#": [
        "https://learn.microsoft.com/en-us/dotnet/csharp/",
        "https://www.freecodecamp.org/news/learn-c-sharp-programming/",
    ],
    "go": [
        "https://go.dev/tour/",
        "https://gobyexample.com/",
    ],
    "rust": [
        "https://doc.rust-lang.org/book/",
        "https://rustlings.cool/",
    ],
    "sql": [
        "https://mode.com/sql-tutorial/",
        "https://sqlbolt.com/",
        "https://www.w3schools.com/sql/",
    ],
    "html5": [
        "https://developer.mozilla.org/en-US/docs/Learn/HTML",
        "https://www.freecodecamp.org/learn/2022/responsive-web-design/",
    ],
    "css3": [
        "https://developer.mozilla.org/en-US/docs/Learn/CSS",
        "https://css-tricks.com/snippets/css/a-guide-to-flexbox/",
        "https://css-tricks.com/snippets/css/complete-guide-grid/",
    ],
    "bash": [
        "https://linuxjourney.com/",
        "https://www.freecodecamp.org/news/bash-scripting-tutorial-linux-shell-script-and-command-line-for-beginners/",
    ],

    # Frontend Frameworks
    "react": [
        "https://react.dev/learn",
        "https://egghead.io/courses/the-beginner-s-guide-to-react",
        "https://fullstackopen.com/en/part1",
    ],
    "next.js": [
        "https://nextjs.org/learn",
        "https://nextjs.org/docs",
    ],
    "angular": [
        "https://angular.dev/tutorials",
        "https://angular.dev/overview",
    ],
    "vue": [
        "https://vuejs.org/guide/introduction.html",
        "https://learnvue.co/",
    ],
    "tailwind css": [
        "https://tailwindcss.com/docs/utility-first",
        "https://tailwindui.com/documentation",
    ],
    "redux": [
        "https://redux.js.org/introduction/getting-started",
        "https://redux-toolkit.js.org/tutorials/quick-start",
    ],

    # Backend Frameworks & APIs
    "node.js": [
        "https://nodejs.org/en/learn",
        "https://nodejs.dev/en/learn/",
    ],
    "fastapi": [
        "https://fastapi.tiangolo.com/tutorial/",
        "https://realpython.com/fastapi-python-web-apis/",
    ],
    "django": [
        "https://docs.djangoproject.com/en/stable/intro/tutorial01/",
        "https://www.tangowithdjango.com/",
    ],
    "flask": [
        "https://flask.palletsprojects.com/en/stable/tutorial/",
    ],
    "spring boot": [
        "https://spring.io/guides/gs/spring-boot/",
        "https://www.baeldung.com/spring-boot",
    ],
    "express": [
        "https://expressjs.com/en/starter/installing.html",
        "https://developer.mozilla.org/en-US/docs/Learn/Server-side/Express_Nodejs",
    ],
    "graphql": [
        "https://graphql.org/learn/",
        "https://www.howtographql.com/",
    ],
    "rest apis": [
        "https://restfulapi.net/",
        "https://www.freecodecamp.org/news/rest-api-design-best-practices/",
    ],

    # Databases & Caching
    "postgresql": [
        "https://www.postgresqltutorial.com/",
        "https://postgrescheatsheet.com/",
    ],
    "mongodb": [
        "https://learn.mongodb.com/",
        "https://www.mongodb.com/docs/manual/tutorial/getting-started/",
    ],
    "mysql": [
        "https://dev.mysql.com/doc/refman/8.0/en/tutorial.html",
        "https://www.mysqltutorial.org/",
    ],
    "redis": [
        "https://redis.io/learn",
        "https://redis.io/docs/latest/develop/get-started/",
    ],
    "elasticsearch": [
        "https://www.elastic.co/guide/en/elasticsearch/reference/current/getting-started.html",
    ],

    # Cloud & DevOps
    "docker": [
        "https://docs.docker.com/get-started/",
        "https://www.freecodecamp.org/news/docker-tutorial/",
        "https://docker-curriculum.com/",
    ],
    "kubernetes": [
        "https://kubernetes.io/docs/tutorials/kubernetes-basics/",
        "https://kubeacademy.vmware.com/",
    ],
    "aws": [
        "https://aws.amazon.com/getting-started/",
        "https://aws.amazon.com/training/digital/",
        "https://www.freecodecamp.org/news/aws-certified-cloud-practitioner-study-guide/",
    ],
    "microsoft azure": [
        "https://learn.microsoft.com/en-us/training/azure/",
    ],
    "google cloud platform": [
        "https://cloud.google.com/training",
    ],
    "ci/cd": [
        "https://docs.github.com/en/actions/learn-github-actions",
        "https://www.atlassian.com/continuous-delivery/principles",
    ],
    "terraform": [
        "https://developer.hashicorp.com/terraform/tutorials",
    ],
    "git": [
        "https://git-scm.com/book/en/v2",
        "https://learngitbranching.js.org/",
    ],
    "linux": [
        "https://linuxjourney.com/",
        "https://overthewire.org/wargames/bandit/",
    ],

    # AI, ML & Data
    "machine learning": [
        "https://www.coursera.org/learn/machine-learning",
        "https://developers.google.com/machine-learning/crash-course",
    ],
    "deep learning": [
        "https://www.deeplearning.ai/",
        "https://d2l.ai/",
    ],
    "pytorch": [
        "https://pytorch.org/tutorials/beginner/basics/intro.html",
        "https://pytorch.org/tutorials/",
    ],
    "tensorflow": [
        "https://www.tensorflow.org/tutorials",
    ],
    "scikit-learn": [
        "https://scikit-learn.org/stable/getting_started.html",
    ],
    "pandas": [
        "https://pandas.pydata.org/docs/getting_started/index.html",
        "https://www.kaggle.com/learn/pandas",
    ],

    # Core CS & Architecture
    "data structures": [
        "https://www.geeksforgeeks.org/data-structures/",
        "https://visualgo.net/",
        "https://leetcode.com/explore/",
    ],
    "algorithms": [
        "https://github.com/trekhleb/javascript-algorithms",
        "https://visualgo.net/",
        "https://leetcode.com/explore/",
    ],
    "system design": [
        "https://github.com/donnemartin/system-design-primer",
        "https://bytebytego.com/",
    ],
    "microservices": [
        "https://microservices.io/",
    ],
    "unit testing": [
        "https://martinfowler.com/articles/practical-test-pyramid.html",
    ],
    "kafka": [
        "https://kafka.apache.org/documentation/",
        "https://developer.confluent.io/quickstart/kafka-local/",
    ],
}

import re

RESOURCE_SYNONYMS = {
    "golang": "go",
    "postgres": "postgresql",
    "k8s": "kubernetes",
    "js": "javascript",
    "ts": "typescript",
    "gcp": "google cloud platform",
    "azure": "microsoft azure",
    "restful apis": "rest apis",
    "restful api design": "rest apis",
    "rest api": "rest apis",
    "api design": "rest apis",
    "version control": "git",
    "git & version control": "git",
    "data structures & algorithms": "data structures",
    "dsa": "data structures",
    "relational databases": "sql",
    "relational database design": "sql",
    "sql querying": "sql",
    "continuous integration": "ci/cd",
    "continuous delivery": "ci/cd",
    "github actions": "ci/cd",
    "testing": "unit testing",
}


def get_resources_for_skill(skill: str) -> list[str]:
    key = skill.lower().strip()
    
    # 1. Direct exact match
    if key in SKILL_RESOURCES:
        return SKILL_RESOURCES[key]
    
    # 2. Canonical synonym match
    if key in RESOURCE_SYNONYMS and RESOURCE_SYNONYMS[key] in SKILL_RESOURCES:
        return SKILL_RESOURCES[RESOURCE_SYNONYMS[key]]
    
    # 3. Safe token / word-boundary match
    # Sort keys descending by length so longer, more specific keys (e.g. 'javascript')
    # match before shorter keys (e.g. 'java').
    # Word-boundary (\b) ensures short tokens like 'go' only match standalone words,
    # never substrings inside words like 'pedagogy', 'negotiation', 'cargo', etc.
    for k, urls in sorted(SKILL_RESOURCES.items(), key=lambda item: len(item[0]), reverse=True):
        pattern = rf"\b{re.escape(k)}\b"
        if re.search(pattern, key):
            return urls

    # 4. Honest fallback: If no curated resource is verified, return empty list rather than
    # fabricating a generic search URL (Phase 16E requirement)
    return []

