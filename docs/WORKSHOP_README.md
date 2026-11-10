# How to use LLMs to present results from your research project as a web application: hands-on session

This repository contains instructions and examples for the hands-on session of the workshop **How to use LLMs to present results from your research project as a web application** that is held on 2026-11-10 as part of the [DDLS Annual Conference 2026](https://www.scilifelab.se/event/ddls-annual-conference-2026/).

During this hands-on session, we encourage participants to build web apps for their own projects. In case you do not have such a project, you can use one of the three example datasets and/or code that we prepared. Each folder in this repository contains one example. You can either use `git clone` to copy the content of this repository to your computer or download it (select *Code* -> *Download ZIP* above).

## Suggested steps during this hands-on exercise:

1. Decide on your own project to work on or select one of the three examples that we prepared. You should understand what the dataset contains or what the ML model does and have an idea for what you wish to achieve with the web app.

2. Share the template for web applications that we prepared with the AI assistance tool of your choice (use anything you are used to using, it should work). The template is located here: [https://github.com/ScilifelabDataCentre/serve-app-template](https://github.com/ScilifelabDataCentre/serve-app-template). Your first prompt could be something like this:

> Read from https://serve.scilifelab.se/docs/application-hosting/shiny/_source/ so I can ask questions about it.
> For additional information or guidance on creating apps, also refer to https://github.com/ScilifelabDataCentre/serve-app-template.

3. Share the dataset(s), code, model weights, etc. from your project with your AI assistance tool so that they are loaded into the memory or otherwise available to it.

4. Write a prompt to create a simple first version of your web application: specify the data definition, interactions, expected output, and checks. Build and run: make a minimal version, fix errors, and avoid unnecessary features. Iteratively add/change elements.

5. When you are happy with the result, verify the behavior: e.g., look at the code and make sure it is doing what it should do, compare a plotted value with the original data; test empty filters analysis, independently check one prediction calculation, etc. Make use of your skeptical scientist mindsent to investigate it and make sure you are comfortable with putting your name behind what it does. Keep in mind that it is always you who is ultimately responsible for correctness of the web app behavior.

6. Wrap up and share (optional): Prepare your web app for sharing through SciLifeLab Serve (using the instructions that your AI assistant generates for you based on our template or by following SciLifeLab Serve user documentation), and add your app with visibility Project/Private to test it.

## Questions?

The instructors are happy to help and answer your questions on the spot during the workshop. Feel free to reach other with other questions afterwards: serve@scilifelab.se.

## Authors

This workshop was prepared by the SciLifeLab Data Centre team.