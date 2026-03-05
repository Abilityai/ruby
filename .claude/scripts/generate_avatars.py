#!/usr/bin/env python3
"""
Generate YouTube channel avatar options using Gemini Image API.
Uses reference photos of the creator for likeness consistency.
"""

import sys
import time
from pathlib import Path

# Add path for imports
sys.path.insert(0, str(Path(__file__).parent / "repurpose"))
sys.path.insert(0, str(Path(__file__).parent / "repurpose" / "utils"))

from gemini_image import download_reference_photos, generate_image, save_image

# Avatar prompts - varied styles for YouTube channel profile
AVATAR_PROMPTS = [
    # 1. Professional headshot
    """Professional YouTube channel avatar portrait of the person in the reference photos.
    Clean, minimalist background with subtle light gray gradient.
    Warm, approachable expression with confident slight smile.
    Professional lighting with soft shadows.
    High-quality studio photography look.
    Square format, optimized for circular crop.""",

    # 2. Tech/AI themed
    """Modern tech entrepreneur avatar portrait of the person in the reference photos.
    Dark background with subtle blue/purple tech-inspired glow effects.
    Subject looking slightly off-camera with thoughtful expression.
    Holographic or digital elements subtly integrated in background.
    Professional but edgy tech founder aesthetic.
    Square format for YouTube channel.""",

    # 3. Bold with accent color
    """Bold YouTube avatar of the person in the reference photos.
    Clean white background with a vibrant red circular accent or shape behind the head.
    Confident, direct eye contact with viewer.
    Sharp, high contrast photography style.
    Energetic and attention-grabbing composition.
    Square format, works when cropped to circle.""",

    # 4. Thought leader/speaker style
    """Thought leader portrait avatar of the person in the reference photos.
    Warm, professional setting with blurred neutral background.
    Engaged expression, mid-conversation look.
    Natural lighting with golden hour warmth.
    Authoritative but approachable presence.
    Square format for profile picture.""",

    # 5. Minimalist artistic
    """Artistic minimalist avatar portrait of the person in the reference photos.
    Pure clean background in off-white or very light gray.
    Simple, elegant composition focused on face.
    Subtle catchlights in eyes.
    Editorial photography style, slightly desaturated tones.
    Square format, dramatic use of negative space.""",

    # 6. Dynamic/energetic
    """Dynamic, energetic YouTube avatar of the person in the reference photos.
    Gradient background transitioning from deep blue to electric teal.
    Animated expression showing enthusiasm and energy.
    Modern, fresh composition with slight angle.
    Vibrant but professional color treatment.
    Square format, engaging and memorable.""",

    # 7. Studio podcast style
    """Professional podcast/studio avatar of the person in the reference photos.
    Dark, moody studio background with professional lighting.
    Confident, commanding presence.
    Rim lighting creating depth and dimension.
    Premium content creator aesthetic.
    Square format optimized for circular avatar crop.""",

    # 8. Clean modern
    """Ultra-clean modern avatar portrait of the person in the reference photos.
    Solid pastel or muted color background (sage green or dusty blue).
    Natural, relaxed expression with genuine warmth.
    Soft, even lighting with no harsh shadows.
    Contemporary, approachable style.
    Square format, social media optimized.""",

    # 9. Bold contrast
    """High contrast dramatic avatar of the person in the reference photos.
    Black background with dramatic directional lighting.
    Serious, focused expression showing expertise and depth.
    Chiaroscuro lighting technique.
    Powerful, memorable impression.
    Square format for channel branding.""",

    # 10. Friendly casual
    """Warm, friendly avatar portrait of the person in the reference photos.
    Soft gradient background in warm neutral tones.
    Genuine smile, approachable and trustworthy expression.
    Natural, authentic feel - not overly produced.
    Relatable content creator vibe.
    Square format, inviting and personable.""",
]


def main():
    output_dir = Path.home() / "Downloads" / f"YouTube_Avatars_{time.strftime('%Y-%m-%d')}"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("YouTube Avatar Generator")
    print("=" * 60)

    # Download reference photos
    print("\nDownloading reference photos...")
    reference_photos = download_reference_photos(max_photos=6)
    if not reference_photos:
        print("Error: No reference photos available")
        sys.exit(1)
    print(f"Using {len(reference_photos)} reference photos")

    # Generate avatars
    print(f"\nGenerating {len(AVATAR_PROMPTS)} avatar options...")

    successful = 0
    for i, prompt in enumerate(AVATAR_PROMPTS, 1):
        print(f"\n[{i}/{len(AVATAR_PROMPTS)}] Generating avatar style {i}...")

        # Generate image with 1:1 aspect ratio for avatars
        image_data = generate_image(
            prompt=prompt,
            reference_photos=reference_photos,
            aspect_ratio="1:1",  # Square for avatars
        )

        if image_data:
            output_path = output_dir / f"avatar_{i:02d}.png"
            if save_image(image_data, output_path):
                successful += 1
                print(f"    Saved: {output_path.name}")
            else:
                print(f"    Error: Failed to save")
        else:
            print(f"    Error: Failed to generate")

        # Rate limiting between generations
        if i < len(AVATAR_PROMPTS):
            time.sleep(2)

    print("\n" + "=" * 60)
    print(f"Avatar Generation Complete")
    print("=" * 60)
    print(f"  Generated: {successful}/{len(AVATAR_PROMPTS)}")
    print(f"  Location: {output_dir}")
    print("\n  open " + str(output_dir))


if __name__ == "__main__":
    main()
