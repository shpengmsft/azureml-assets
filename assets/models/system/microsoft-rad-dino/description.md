## Model Description

# Model card for RAD-DINO

## Model description

RAD-DINO is a vision transformer model trained to encode chest X-rays using the self-supervised learning method [DINOv2](https://openreview.net/forum?id=a68SUt6zFt).

RAD-DINO is described in detail in [RAD-DINO: Exploring Scalable Medical Image Encoders Beyond Text Supervision (F. Pérez-García, H. Sharma, S. Bond-Taylor, et al., 2024)](https://arxiv.org/abs/2401.10815).

- **Developed by:** Microsoft Health Futures
- **Model type:** Vision transformer
- **License:** MSRLA
- **Finetuned from model:** [`dinov2-base`](https://huggingface.co/facebook/dinov2-base)

## Uses

RAD-DINO is shared for research purposes only.
It is **not meant to be used for clinical practice**.

The model is a vision backbone that can be plugged to other models for downstream tasks.
Some potential uses are:

- Image classification, with a classifier trained on top of the `CLS` token
- Image segmentation, with a decoder trained using the patch tokens
- Clustering, using the image embeddings directly
- Image retrieval, using nearest neighbors of the CLS token
- Report generation, with a language model to decode text

Fine-tuning RAD-DINO is typically not necessary to obtain good performance in downstream tasks.

## Biases, risks, and limitations

RAD-DINO was trained with data from three countries, therefore it might be biased towards population in the training data.
Underlying biases of the training datasets may not be well characterized.

## Getting started

Let us first write an auxiliary function to download a chest X-ray.

```python
>>> import requests
>>> from PIL import Image
>>> def download_sample_image() -> Image.Image:
...     """Download chest X-ray with CC license."""
...     base_url = "https://upload.wikimedia.org/wikipedia/commons"
...     image_url = f"{base_url}/2/20/Chest_X-ray_in_influenza_and_Haemophilus_influenzae.jpg"
...     headers = {"User-Agent": "RAD-DINO"}
...     response = requests.get(image_url, headers=headers, stream=True)
...     return Image.open(response.raw)
...
```

Now let us download the model and encode an image.

```python
>>> import torch
>>> from transformers import AutoModel
>>> from transformers import AutoImageProcessor
>>>
>>> # Download the model
>>> repo = "microsoft/rad-dino"
>>> model = AutoModel.from_pretrained(repo)
>>>
>>> # The processor takes a PIL image, performs resizing, center-cropping, and
>>> # intensity normalization using stats from MIMIC-CXR, and returns a
>>> # dictionary with a PyTorch tensor ready for the encoder
>>> processor = AutoImageProcessor.from_pretrained(repo)
>>>
>>> # Download and preprocess a chest X-ray
>>> image = download_sample_image()
>>> image.size  # (width, height)
(2765, 2505)
>>> inputs = processor(images=image, return_tensors="pt")
>>>
>>> # Encode the image!
>>> with torch.inference_mode():
>>>     outputs = model(**inputs)
>>>
>>> # Look at the CLS embeddings
>>> cls_embeddings = outputs.pooler_output
>>> cls_embeddings.shape  # (batch_size, num_channels)
torch.Size([1, 768])
```

If we are interested in the feature maps, we can reshape the patch embeddings into a grid.
We will use [`einops`](https://einops.rocks/) (install with `pip install einops`) for this.

```python
>>> def reshape_patch_embeddings(flat_tokens: torch.Tensor) -> torch.Tensor:
...     """Reshape flat list of patch tokens into a nice grid."""
...     from einops import rearrange
...     image_size = processor.crop_size["height"]
...     patch_size = model.config.patch_size
...     embeddings_size = image_size // patch_size
...     patches_grid = rearrange(flat_tokens, "b (h w) c -> b c h w", h=embeddings_size)
...     return patches_grid
...
>>> flat_patch_embeddings = outputs.last_hidden_state[:, 1:]  # first token is CLS
>>> reshaped_patch_embeddings = reshape_patch_embeddings(flat_patch_embeddings)
>>> reshaped_patch_embeddings.shape  # (batch_size, num_channels, height, width)
torch.Size([1, 768, 37, 37])
```

## Training details

### Training data

We used images from five public, deidentified chest X-ray datasets to train this checkpoint of RAD-DINO.

| Dataset   | Num. images |
| --------- | ----------: |
| [MIMIC-CXR](https://www.nature.com/articles/s41597-019-0322-0) | 368 960 |
| [CheXpert](https://ojs.aaai.org/index.php/AAAI/article/view/3834) | 223 648 |
| [NIH-CXR](https://openaccess.thecvf.com/content_cvpr_2017/html/Wang_ChestX-ray8_Hospital-Scale_Chest_CVPR_2017_paper.html) | 112 120 |
| [PadChest](https://www.sciencedirect.com/science/article/abs/pii/S1361841520301614) | 136 787 |
| [BRAX](https://www.nature.com/articles/s41597-022-01608-8) | 41 260 |
| **TOTAL** | 882 775 |

Images in the validation and test sets used to train [MAIRA](https://arxiv.org/abs/2311.13668) were excluded from the training set of RAD-DINO.
The list of image files used for training is available at [`./training_images.csv`](./training_images.csv).

Note this checkpoint is different from the one in the paper, where some private data was used (and fewer GPUs).
The checkpoint shared here is trained for 35 000 iterations (the total number of iterations in the run was 100 000, but we selected this checkpoint using linear probing on the validation sets of the evaluation datasets described in the paper).
We used 16 nodes with 4 A100 GPUs each, and a batch size of 40 images per GPU.

### Training procedure

We refer to the [manuscript](https://arxiv.org/abs/2401.10815) for a detailed description of the training procedure.

#### Preprocessing

All DICOM files were resized using B-spline interpolation so that their shorter size was 518, min-max scaled to [0, 255], and stored as PNG files.

#### Training hyperparameters

- **Training regime:** fp16 using PyTorch-FSDP mixed-precision.

## Evaluation

Our evaluation is best described in the [manuscript](https://arxiv.org/abs/2401.10815).

## Environmental impact

- **Hardware type:** NVIDIA A100 GPUs
- **Hours used:** 40 hours/GPU × 16 nodes × 4 GPUs/node = 2560 GPU-hours
- **Cloud provider:** Azure
- **Compute region:** West US 2
- **Carbon emitted:** 222 kg CO₂ eq.

### Compute infrastructure

RAD-DINO was trained on [Azure Machine Learning](https://azure.microsoft.com/en-us/products/machine-learning).

#### Hardware

We used 16 `Standard_NC96ads_A100_v4` nodes with four NVIDIA A100 (80 GB) GPUs each.

#### Software

We leveraged the code in [DINOv2](https://openreview.net/forum?id=a68SUt6zFt) for training.
We used [SimpleITK](https://simpleitk.org/) and [Pydicom](https://pydicom.github.io/) for processing of DICOM files.

## Citation

**BibTeX:**

```bibtex
@misc{perezgarcia2024raddino,
      title={{RAD-DINO}: Exploring Scalable Medical Image Encoders Beyond Text Supervision},
      author={Fernando Pérez-García and Harshita Sharma and Sam Bond-Taylor and Kenza Bouzid and Valentina Salvatelli and Maximilian Ilse and Shruthi Bannur and Daniel C. Castro and Anton Schwaighofer and Matthew P. Lungren and Maria Wetscherek and Noel Codella and Stephanie L. Hyland and Javier Alvarez-Valle and Ozan Oktay},
      year={2024},
      eprint={2401.10815},
      archivePrefix={arXiv},
      primaryClass={cs.CV}
}
```

**APA:**

> Pérez-García, F., Sharma, H., Bond-Taylor, S., Bouzid, K., Salvatelli, V., Ilse, M., Bannur, S., Castro, D.C., Schwaighofer, A., Lungren, M.P., Wetscherek, M.T., Codella, N., Hyland, S.L., Alvarez-Valle, J., & Oktay, O. (2024). *RAD-DINO: Exploring Scalable Medical Image Encoders Beyond Text Supervision*. ArXiv, abs/2401.10815.

### Inference samples

Inference type|Python sample (Notebook)|CLI with YAML
|--|--|--|
Real time|<a href="https://aka.ms/azureml-infer-sdk-image-embeddings" target="_blank">image-embeddings-online-endpoint.ipynb</a>|<a href="https://aka.ms/azureml-infer-cli-image-embeddings" target="_blank">image-embeddings-online-endpoint.sh</a>

### Sample inputs and outputs

#### Sample input
```json
{"input_data": {"columns": ["image"], "index": [0], "data": ["image1"]}}
```

#### Sample output
```json
[{"image_features": [0.0, 0.0, 0.0]}]
```
