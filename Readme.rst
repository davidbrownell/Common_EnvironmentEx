====================
Common_EnvironmentEx
====================

Enhances `Common_Environment` with libraries, scripts, and tools common to different development activities. `Common_Environment` is focused
on minimalisim, while `Common_EnvironmentEx` is focused on utility.

Contents
========
#. `Quick Start`_
#. License_
#. `Supported Platforms`_
#. Definitions_
#. Functionality_
#. `Docker Images`_
#. Dependencies_
#. Support_

Quick Start
===========
Setup_ and Activate_ are required to begin using this repository. Before running these scripts, please make sure that all Dependencies_ have been cloned.

.. _Setup:

Setup
  Setup installs/unpacks tools used during development activities and locates its repository dependencies (if any). Setup must be run on your machine after cloning the repository or after changing the file location of repositories that it depends upon (if any).

  ====================================  =====================================================
  Linux                                 ``Setup.sh``
  Windows                               ``Setup.cmd``
  Windows (PowerShell)                  ``Setup.ps1``
  ====================================  =====================================================
  
.. _Activate:

Activate
  Activate prepares the current environment for development activities and must be run at least once in each terminal window.
  
  ====================================  =====================================================
  Linux                                 ``Activate.sh <TODO: Update configurations>``
  Windows                               ``Activate.cmd <TODO: Update configurations>``
  Windows (PowerShell)                  ``Activate.ps1 <TODO: Update configurations>``
  ====================================  =====================================================
  
License
=======
This repository is licensed under the `Boost Software License <https://www.boost.org/LICENSE_1_0.txt>`_. 

`GitHub <https://github.com>`_ describes this license as:

  A simple permissive license only requiring preservation of copyright and license notices for source (and not binary) distribution. Licensed works, modifications, and larger works may be distributed under different terms and without source code.

Supported Platforms
===================
This software has been verified on the following platforms.

========================  ======================  =========================================
Platform                  Scripting Environment   Version
========================  ======================  =========================================
Windows                   Cmd.exe                 Windows 10 April 2018 Update
Windows                   PowerShell              Windows 10 April 2018 Update
Linux                     Bash                    Ubuntu 18.04, 16.04
========================  ======================  =========================================

Definitions
===========
  
Functionality
=============
  
Docker Images
=============
Docker images of `Common_EnvironmentEx` are generated periodically.

==========================  ==========================================
Coming Soon                 An environment that is setup but not activated (useful as a base image).
Coming Soon                 An environment that is activated.
==========================  ==========================================

Dependencies
============
This repository is dependent upon these repositories.

==============================  =================================
Repo Name                       Description
==============================  =================================
`Common_Environment`            Common development activities
==============================  =================================

Support
=======
For question or issues, please visit <TODO: Your url>.
