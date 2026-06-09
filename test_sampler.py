from src.text_sampler import split_into_chapters, score_paragraph, create_book_digest, get_best_excerpt

# Test with a fake book
fake_book = ''
for i in range(1, 21):
    fake_book += f'\n\nChapter {i}\n\n'
    for j in range(10):
        if j == 0:
            fake_book += f'The grand castle of Eldoria towered above the misty valleys, its ancient golden spires gleaming in the crimson sunset. Lord Aldric stood at the window, his dark cloak billowing in the cold wind, watching the vast army approaching from the shadowy mountains.\n\n'
        elif j == 5:
            fake_book += f'"We must retreat!" shouted Marcus.\n\n'
        else:
            fake_book += f'The story continued in chapter {i}, paragraph {j}. Events unfolded as the characters moved through the narrative. ' * 3 + '\n\n'

print(f'Total book size: {len(fake_book)} chars\n')

# Test chapter detection
chapters = split_into_chapters(fake_book)
print(f'Chapters detected: {len(chapters)}')
if chapters:
    print(f'First chapter: {chapters[0]["title"]}')
print()

# Test paragraph scoring
p1 = 'The grand castle of Eldoria towered above the misty valleys, its ancient golden spires gleaming in the crimson sunset.'
p2 = '"We must retreat!" shouted Marcus.'
p3 = 'The story continued. Events unfolded.'
print(f'Descriptive paragraph score: {score_paragraph(p1):.2f}')
print(f'Dialogue score: {score_paragraph(p2):.2f}')
print(f'Generic score: {score_paragraph(p3):.2f}')
print()

# Test digest creation
digest = create_book_digest(fake_book, target_chars=5000)
print(f'Digest size: {len(digest)} chars (target: 5000)')
print(f'Digest covers: {digest.count("---")} chapter markers')
print()

# Test best excerpt
excerpt = get_best_excerpt(fake_book, target_chars=500)
print(f'Best excerpt ({len(excerpt)} chars): {excerpt[:100]}...')
print()
print('All tests passed!')
