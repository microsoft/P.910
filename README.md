# P.910 Crowd

The P.910-Crowd Toolkit is a software package designed to enable users to conduct subjective video quality assessment tests on crowdsourcing platforms like Amazon Mechanical Turk (AMT) or through remote testing with a dedicated panel of workers. It serves as a counterpart to the ITU-T Recommendation P.910 for crowdsourcing.



**Note**: Full-screen playback is currently not supported by HITs built within AMT. To address this, we provide the [HITAPP Server](hitapp_server/README.md), which can host the experiment. This allows you to use AMT or any other crowdsourcing platform by posting your study URL.

For more information about ITU-T Recommendation P.910, refer to:

[ITU-T Recommendation P.910, _Subjective video quality assessment methods for multimedia applications._](https://www.itu.int/rec/T-REC-P.910/en)  
Geneva: International Telecommunication Union, 2021.

A technical description of the implementation and validation is provided in the following papers:

* "[_A crowdsourcing approach to video quality assessment_](https://arxiv.org/pdf/2204.06784.pdf)," Babak Naderi, Ross Cutler, ICASSP 2024 and arXiv preprint 2022.

* "[_A multidimensional measurement of Photorealistic Avatar Quality of Experience_](https://arxiv.org/pdf/2411.09066)," Ross Cutler, Babak Naderi, Vishak Gopal, Dharmendar Palle, CSCW 2025.

### Updates
* **April 2025**: The toolkit has been updated to support multi-dimensional measurement of the quality of experience for Photorealistic Avatars.


## Citation
If you use this toolkit in your research, please cite it using the following references:

```BibTex
@article{naderi2024,
  title={A crowdsourcing approach to video quality assessment},
  author={Naderi, Babak and Cutler, Ross},
  booktitle={ICASSP},
  year={2024}
}

@article{cutler2024multidimensional,
  title={A multidimensional measurement of photorealistic avatar quality of experience},
  author={Cutler, Ross and Naderi, Babak and Gopal, Vishak and Palle, Dharmendar},
  journal={CSCW},
  year={2025}
}
```

## Getting Started
* [Preparation](docs/preparation.md)
* [Running the Crowdsourcing Test](docs/running_test_mturk.md)
* [Analyzing Data](docs/results.md)

## Troubleshooting
For bug reports and issues with this code, please see the 
[_github issues page_](https://github.com/microsoft/P.910/issues). Please review this page before contacting the authors.

## Contact

Contact [Ross Cutler](mailto:rcutler@microsoft.com) with any questions.

## License
### Code License
MIT License

Copyright (c) Microsoft Corporation.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit https://cla.opensource.microsoft.com.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft 
trademarks or logos is subject to and must follow 
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.

