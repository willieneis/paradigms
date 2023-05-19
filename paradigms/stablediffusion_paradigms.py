from typing import Any, Callable, Dict, List, Optional, Union

import torch
from diffusers.pipelines.stable_diffusion import StableDiffusionPipelineOutput


@torch.no_grad()
def paradigms_forward(
    self,
    prompt: Union[str, List[str]] = None,
    height: Optional[int] = None,
    width: Optional[int] = None,
    num_inference_steps: int = 50,
    parallel: int = 10,
    tolerance: float = 0.1,
    guidance_scale: float = 7.5,
    negative_prompt: Optional[Union[str, List[str]]] = None,
    num_images_per_prompt: Optional[int] = 1,
    eta: float = 0.0,
    generator: Optional[Union[torch.Generator, List[torch.Generator]]] = None,
    latents: Optional[torch.FloatTensor] = None,
    prompt_embeds: Optional[torch.FloatTensor] = None,
    negative_prompt_embeds: Optional[torch.FloatTensor] = None,
    output_type: Optional[str] = "pil",
    return_dict: bool = True,
    callback: Optional[Callable[[int, int, torch.FloatTensor], None]] = None,
    callback_steps: int = 1,
    cross_attention_kwargs: Optional[Dict[str, Any]] = None,
    full_return: bool = False,
):
    r"""
    Function invoked when calling the pipeline for generation.

    Args:
        prompt (`str` or `List[str]`, *optional*):
            The prompt or prompts to guide the image generation. If not defined, one has to pass `prompt_embeds`.
            instead.
        height (`int`, *optional*, defaults to self.unet.config.sample_size * self.vae_scale_factor):
            The height in pixels of the generated image.
        width (`int`, *optional*, defaults to self.unet.config.sample_size * self.vae_scale_factor):
            The width in pixels of the generated image.
        num_inference_steps (`int`, *optional*, defaults to 50):
            The number of denoising steps. More denoising steps usually lead to a higher quality image at the
            expense of slower inference.
        guidance_scale (`float`, *optional*, defaults to 7.5):
            Guidance scale as defined in [Classifier-Free Diffusion Guidance](https://arxiv.org/abs/2207.12598).
            `guidance_scale` is defined as `w` of equation 2. of [Imagen
            Paper](https://arxiv.org/pdf/2205.11487.pdf). Guidance scale is enabled by setting `guidance_scale >
            1`. Higher guidance scale encourages to generate images that are closely linked to the text `prompt`,
            usually at the expense of lower image quality.
        negative_prompt (`str` or `List[str]`, *optional*):
            The prompt or prompts not to guide the image generation. If not defined, one has to pass
            `negative_prompt_embeds`. instead. If not defined, one has to pass `negative_prompt_embeds`. instead.
            Ignored when not using guidance (i.e., ignored if `guidance_scale` is less than `1`).
        num_images_per_prompt (`int`, *optional*, defaults to 1):
            The number of images to generate per prompt.
        eta (`float`, *optional*, defaults to 0.0):
            Corresponds to parameter eta (η) in the DDIM paper: https://arxiv.org/abs/2010.02502. Only applies to
            [`schedulers.DDIMScheduler`], will be ignored for others.
        generator (`torch.Generator` or `List[torch.Generator]`, *optional*):
            One or a list of [torch generator(s)](https://pytorch.org/docs/stable/generated/torch.Generator.html)
            to make generation deterministic.
        latents (`torch.FloatTensor`, *optional*):
            Pre-generated noisy latents, sampled from a Gaussian distribution, to be used as inputs for image
            generation. Can be used to tweak the same generation with different prompts. If not provided, a latents
            tensor will ge generated by sampling using the supplied random `generator`.
        prompt_embeds (`torch.FloatTensor`, *optional*):
            Pre-generated text embeddings. Can be used to easily tweak text inputs, *e.g.* prompt weighting. If not
            provided, text embeddings will be generated from `prompt` input argument.
        negative_prompt_embeds (`torch.FloatTensor`, *optional*):
            Pre-generated negative text embeddings. Can be used to easily tweak text inputs, *e.g.* prompt
            weighting. If not provided, negative_prompt_embeds will be generated from `negative_prompt` input
            argument.
        output_type (`str`, *optional*, defaults to `"pil"`):
            The output format of the generate image. Choose between
            [PIL](https://pillow.readthedocs.io/en/stable/): `PIL.Image.Image` or `np.array`.
        return_dict (`bool`, *optional*, defaults to `True`):
            Whether or not to return a [`~pipelines.stable_diffusion.StableDiffusionPipelineOutput`] instead of a
            plain tuple.
        callback (`Callable`, *optional*):
            A function that will be called every `callback_steps` steps during inference. The function will be
            called with the following arguments: `callback(step: int, timestep: int, latents: torch.FloatTensor)`.
        callback_steps (`int`, *optional*, defaults to 1):
            The frequency at which the `callback` function will be called. If not specified, the callback will be
            called at every step.
        cross_attention_kwargs (`dict`, *optional*):
            A kwargs dictionary that if specified is passed along to the `AttnProcessor` as defined under
            `self.processor` in
            [diffusers.cross_attention](https://github.com/huggingface/diffusers/blob/main/src/diffusers/models/cross_attention.py).

    Examples:

    Returns:
        [`~pipelines.stable_diffusion.StableDiffusionPipelineOutput`] or `tuple`:
        [`~pipelines.stable_diffusion.StableDiffusionPipelineOutput`] if `return_dict` is True, otherwise a `tuple.
        When returning a tuple, the first element is a list with the generated images, and the second element is a
        list of `bool`s denoting whether the corresponding generated image likely represents "not-safe-for-work"
        (nsfw) content, according to the `safety_checker`.
    """

    print("parallel pipeline!", flush=True)

    # 0. Default height and width to unet
    height = height or self.unet.config.sample_size * self.vae_scale_factor
    width = width or self.unet.config.sample_size * self.vae_scale_factor

    # 1. Check inputs. Raise error if not correct
    self.check_inputs(
        prompt, height, width, callback_steps, negative_prompt, prompt_embeds, negative_prompt_embeds
    )

    # 2. Define call parameters
    if prompt is not None and isinstance(prompt, str):
        batch_size = 1
    elif prompt is not None and isinstance(prompt, list):
        batch_size = len(prompt)
    else:
        batch_size = prompt_embeds.shape[0]

    device = self._execution_device
    # here `guidance_scale` is defined analog to the guidance weight `w` of equation (2)
    # of the Imagen paper: https://arxiv.org/pdf/2205.11487.pdf . `guidance_scale = 1`
    # corresponds to doing no classifier free guidance.
    do_classifier_free_guidance = guidance_scale > 1.0

    # 3. Encode input prompt
    prompt_embeds = self._encode_prompt(
        prompt,
        device,
        num_images_per_prompt,
        do_classifier_free_guidance,
        negative_prompt,
        prompt_embeds=prompt_embeds,
        negative_prompt_embeds=negative_prompt_embeds,
    )

    # 4. Prepare timesteps
    self.scheduler.set_timesteps(num_inference_steps, device=device)
    scheduler = self.scheduler

    # 5. Prepare latent variables
    num_channels_latents = self.unet.in_channels
    latents = self.prepare_latents(
        batch_size * num_images_per_prompt,
        num_channels_latents,
        height,
        width,
        prompt_embeds.dtype,
        device,
        generator,
        latents,
    )

    # 6. Prepare extra step kwargs. TODO: Logic should ideally just be moved out of the pipeline
    extra_step_kwargs = self.prepare_extra_step_kwargs(generator, eta)

    # 7. Denoising loop
    # print(scheduler.timesteps)
    stats_pass_count = 0
    stats_flop_count = 0
    parallel = min(parallel, len(scheduler.timesteps))

    begin_idx = 0
    end_idx = parallel
    latents_time_evolution_buffer = torch.stack([latents] * (len(scheduler.timesteps)+1))

    noise_array = torch.zeros_like(latents_time_evolution_buffer)
    for j in range(len(scheduler.timesteps)):
        base_noise = torch.randn_like(latents)
        noise = (self.scheduler._get_variance(scheduler.timesteps[j]) ** 0.5) * base_noise
        noise_array[j] = noise.clone()
    inverse_variance_norm = 1. / torch.tensor([scheduler._get_variance(scheduler.timesteps[j]) for j in range(len(scheduler.timesteps))] + [0]).to(noise_array.device)
    inverse_variance_norm /= noise_array[0].numel()

    scaled_tolerance = (tolerance**2)

    start = torch.cuda.Event(enable_timing=True)
    end = torch.cuda.Event(enable_timing=True)

    start.record()

    while begin_idx < len(scheduler.timesteps):
        # these have shape (parallel_dim, 2*batch_size, ...)
        # parallel_dim is at most parallel, but could be less if we are at the end of the timesteps
        parallel_len = end_idx - begin_idx

        block_prompt_embeds = torch.stack([prompt_embeds] * parallel_len)
        block_latents = latents_time_evolution_buffer[begin_idx:end_idx]
        block_t = scheduler.timesteps[begin_idx:end_idx]
        t_vec = block_t[:, None].repeat(1, 2 * batch_size if do_classifier_free_guidance else batch_size)

        # expand the latents if we are doing classifier free guidance
        latent_model_input = torch.cat([block_latents] * 2, dim=1) if do_classifier_free_guidance else block_latents
        latent_model_input = self.scheduler.scale_model_input(latent_model_input, t_vec)

        net = self.wrapped_unet if parallel_len > 3 else self.unet
        # predict the noise residual
        model_output = net(
            latent_model_input.flatten(0,1),
            t_vec.flatten(0,1),
            encoder_hidden_states=block_prompt_embeds.flatten(0,1),
            cross_attention_kwargs=cross_attention_kwargs,
            return_dict=False,
        )[0]

        if do_classifier_free_guidance:
            noise_pred_uncond, noise_pred_text = model_output[::2], model_output[1::2]
            model_output = noise_pred_uncond + guidance_scale * (noise_pred_text - noise_pred_uncond)

        block_latents_denoise = scheduler.batch_step_no_noise(
            model_output=model_output,
            timesteps=block_t,
            sample=block_latents.flatten(0,1),
            **extra_step_kwargs,
        ).reshape(block_latents.shape)


        # back to shape (parallel_dim, batch_size, ...)
        delta = block_latents_denoise - block_latents
        cumulative_delta = torch.cumsum(delta, dim=0)
        cumulative_noise = torch.cumsum(noise_array[begin_idx:end_idx], dim=0)


        if scheduler._is_ode_scheduler:
            cumulative_noise = 0
        block_latents_new = latents_time_evolution_buffer[begin_idx][None,] + cumulative_delta + cumulative_noise
        cur_error = torch.linalg.norm((block_latents_new - latents_time_evolution_buffer[begin_idx+1:end_idx+1]).reshape(parallel_len, -1), dim=1).pow(2)
        error_ratio = cur_error * inverse_variance_norm[begin_idx+1:end_idx+1]

        # find the first index of the vector error_ratio that is greater than error tolerance
        error_ratio = torch.nn.functional.pad(error_ratio, (0,1), value=1e9) # handle the case when everything is below ratio
        ind = torch.argmax( (error_ratio > scaled_tolerance).int() ).item()

        new_begin_idx = begin_idx + min(1 + ind, parallel)
        new_end_idx = min(new_begin_idx + parallel, len(scheduler.timesteps))

        latents_time_evolution_buffer[begin_idx+1:end_idx+1] = block_latents_new
        latents_time_evolution_buffer[end_idx:new_end_idx+1] = latents_time_evolution_buffer[end_idx][None,] # hopefully better than random initialization

        begin_idx = new_begin_idx
        end_idx = new_end_idx

        stats_pass_count += 1
        stats_flop_count += parallel_len

    latents = latents_time_evolution_buffer[-1]

    print("pass count", stats_pass_count)
    print("flop count", stats_flop_count)

    end.record()

    # Waits for everything to finish running
    torch.cuda.synchronize()

    print(start.elapsed_time(end))
    print("done", flush=True)

    stats = {
        'pass_count': stats_pass_count,
        'flops_count': stats_flop_count,
        'time': start.elapsed_time(end),
    }

    def process_image(latents):
        if output_type == "latent":
            image = latents
            has_nsfw_concept = None
        elif output_type == "pil":
            # 8. Post-processing
            #print("post-processing", flush=True)
            image = self.decode_latents(latents)

            # 9. Run safety checker
            #print("safety check", flush=True)
            image, has_nsfw_concept = self.run_safety_checker(image, device, prompt_embeds.dtype)

            # 10. Convert to PIL
            #print("conver to PIL", flush=True)
            image = self.numpy_to_pil(image)
        else:
            # 8. Post-processing
            image = self.decode_latents(latents)

            # 9. Run safety checker
            image, has_nsfw_concept = self.run_safety_checker(image, device, prompt_embeds.dtype)

        # Offload last model to CPU
        if hasattr(self, "final_offload_hook") and self.final_offload_hook is not None:
            print("offload hook", flush=True)
            self.final_offload_hook.offload()

        return image, has_nsfw_concept


    if full_return:
        output = [process_image(latents) for latents in latents_time_evolution_buffer]

        if not return_dict:
            return [(image, has_nsfw_concept) for (image, has_nsfw_concept) in output]

        return [StableDiffusionPipelineOutput(images=image, nsfw_content_detected=has_nsfw_concept) for (image, has_nsfw_concept) in output]
    else:
        (image, has_nsfw_concept) = process_image(latents)
        
        if not return_dict:
            return (image, has_nsfw_concept)

        return StableDiffusionPipelineOutput(images=image, nsfw_content_detected=has_nsfw_concept), stats
