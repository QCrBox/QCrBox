# Project Phases / Roadmap

## Project Phases and Accomplishments

- Identification and negotiation of requirements combined with explorative prototyping, resulting in iterative refinement of the project vision and scope.

- Empowering developers of crystallographic applications to package up their software and plug it into the QCrBox platform. Our key achievement is being able to support both of the following goals at the same time:

    - Isolation of individual software’s dependencies and installation and the way in which applications expect input (data & parameters); support for both command line and interactive GUI applications, both Linux/Mac and Windows.

    - Consistent integration in the QCrbox platform so that disparate applications can exchange data and be combined into coherent workflows.

    We have optimised the process to eliminate the need for specialised technical knowledge as much as possible. We are continuously improving the tooling and reducing the amount of work needed by developers to integrate their software into QCrBox.

- Robust architectural design. We used the integration of the following existing crystallographic applications to inform the design process and validation:

    - Olex2
    - CrysAlisPro
    - CrystalExplorer
    - MoPro
    - Eval
    - XHARPy
    - ... _integration of further software is ongoing_ ...


- Graphical User Interface (GUI): We have created a set of target designs in close communication with the community. These ideas form the basis for the formal frontend development which has started recently. In the meantime we have implemented a set of prototype GUIs to test the interaction of different components of QCrBox. A quantum crystallographic example workflow in one of these prototypes can be found in the following video:

    <a href="https://www.youtube.com/watch?v=2x1SuYvV7VE" target="_blank" style="display:flex; justify-content:center;">
      <img src="https://img.youtube.com/vi/2x1SuYvV7VE/0.jpg" width="350">
    </a>


- Tooling to ensure an easy and smooth experience for developers
    - Easy script-based installation
    - Automatic setup of development environment
    - Interactive dialog-driven templating for integrating new software into QCrBox
    - Command line tool as the “entrypoint” for interacting with any aspects of QCrBox (e.g. deployment, starting/stopping containerised applications; invoking non-interactive commands)
    - Python module for high-level programmatic interaction with QCrBox (via the API)

- Documentation (incl. project overview, tutorials, how-to guides)


## Ongoing Work / Roadmap

- Development of the user-facing graphical interface to build and run crystallographic workflows via the QCrBox platform
- Data management & decentralised data handling
- Gathering feedback from users & developers and enhancing the experience of working with QCrBox
- Optimising the deployment experience & support for multi-user setups
- Enhancing support for different deployment scenarios, e.g:
    - Cloud-based deployments
    - Dedicated server hosted & managed by a university department or group
    - Installation on personal devices (laptop or desktop computer)


## Events

|               Date | Location              | Event                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
|-------------------:|:----------------------|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|       3-7 Apr 2023 | Sheffield, UK         | BCA                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
|     22-29 Aug 2023 | Melbourne, Australia  | <div>IUCr<ul><li>H.&nbsp;Puschmann accepted presentation&nbsp;&nbsp;<a href="https://docs.google.com/presentation/d/1c7383aPAPVFBPCYa45xnhbSeg1khvF_A5Bci2M4ND98/edit?usp=sharing" target="_blank"><small>:fontawesome-regular-up-right-from-square:</small> slides</a></li><li>Workshop for the crystallographic community&nbsp;&nbsp;<a href="https://docs.google.com/document/d/1M517EJ2NejBm2MbcI5cBdMeGH_mIDrqJWJ7hjOwGzWw/edit#heading=h.kcfkja2tnb9c" target="_blank"><small>:fontawesome-regular-up-right-from-square:</small> flyer</a></li><li>Workshop for developers of crystallographic software&nbsp;&nbsp;<a href="https://docs.google.com/document/d/1M517EJ2NejBm2MbcI5cBdMeGH_mIDrqJWJ7hjOwGzWw/edit#heading=h.kcfkja2tnb9c" target="_blank"><small>:fontawesome-regular-up-right-from-square:</small> flyer</a></li></ul></div> |
|       4-8 Sep 2023 | Swansea, UK           | <div>RSEcon23<ul><li><a href="https://virtual.oxfordabstracts.com/event/4430/submission/88" target="_blank"><small>:fontawesome-regular-up-right-from-square:</small> Abstract</a></li><li><a href="https://docs.google.com/presentation/d/17ekONfoFVu8mVkcM1ubtqPWMfq3j2EP_tptsAzYiEz0/edit#slide=id.g27b5c318fa7_0_1472" target="_blank"><small>:fontawesome-regular-up-right-from-square:</small> Presentation slides</a></li><li><a href="https://d3ijlhudpq9yjw.cloudfront.net/5861f1a4-5240-488b-9674-72f906e52ade.02%20-%20Part%202%20-%20Tending%20the%20research%20software%20ecosystem%20garden%20-%20Maximilian%20Albert%20-%20Submision%2088" target="_blank"><small>:fontawesome-regular-up-right-from-square:</small> Architecture and design details</a></li></ul></div>                                                            |
|     25-28 Mar 2024 | Leeds, UK             | BCA                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
|     13-14 May 2024 | Durham, UK            | Internal QCrBox project planning meeting                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
|     26-30 Aug 2024 | Padova, Italy         | [ECM](https://www.ecm34.org/)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| 30 Sep-02 Oct 2024 | Neu-Isenburg, Germany | [YCM](https://rigaku.com/products/crystallography/young-crystallographers-meeting-2024)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
