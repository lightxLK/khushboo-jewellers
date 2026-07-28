document.addEventListener('DOMContentLoaded', function () {
    const megaContents = document.querySelectorAll('.mega-menu-content');
    if (megaContents.length === 0) return;

    let allSegments = [];
    let allCategories = [];
    let allSubcategories = {};

    Promise.all([
        fetch('/api/segments').then(r => r.json()),
        fetch('/api/categories').then(r => r.json())
    ]).then(([segments, categories]) => {
        allSegments = segments;
        allCategories = categories;

        megaContents.forEach(megaContent => {
            megaContent.innerHTML = `
            <div class="mega-column segments-column" style="height: 480px; overflow-y: auto;">
                <div class="mega-column-title">Collections</div>
                <div class="segments-list"></div>
            </div>
            <div class="mega-column categories-column" style="height: 480px; overflow-y: auto; display: none;">
                <div class="mega-column-title">Categories</div>
                <div class="categories-list"></div>
            </div>
            <div class="mega-column subcategories-column" style="height: 480px; overflow-y: auto; display: none;">
                <div class="mega-column-title">Subcategories</div>
                <div class="subcategories-list"></div>
            </div>
            `;

            const segmentsList = megaContent.querySelector('.segments-list');
            const categoriesColumn = megaContent.querySelector('.categories-column');
            const categoriesList = megaContent.querySelector('.categories-list');
            const subcategoriesColumn = megaContent.querySelector('.subcategories-column');
            const subcategoriesList = megaContent.querySelector('.subcategories-list');

            const sortedSegments = allSegments.sort((a, b) => a.name.localeCompare(b.name));

            sortedSegments.forEach(segment => {
                const segmentDiv = document.createElement('div');
                segmentDiv.className = 'mega-segment-item';
                segmentDiv.textContent = segment.name;
                segmentDiv.dataset.segmentId = segment.id;

                segmentDiv.addEventListener('click', function () {
                    window.location.href = `/categories/${segment.id}`;
                });

                segmentDiv.addEventListener('mouseenter', function () {
                    megaContent.querySelectorAll('.mega-segment-item').forEach(s => s.classList.remove('active'));
                    this.classList.add('active');

                    categoriesColumn.style.display = 'block';
                    subcategoriesColumn.style.display = 'none';

                    const segmentCategories = allCategories.filter(c => c.segment_id === segment.id);

                    if (segmentCategories.length === 0) {
                        categoriesList.innerHTML = '<div class="mega-empty">No categories</div>';
                    } else {
                        categoriesList.innerHTML = '';
                        segmentCategories.forEach(category => {
                            const categoryDiv = document.createElement('div');
                            categoryDiv.className = 'mega-category-item';
                            categoryDiv.textContent = category.name;
                            categoryDiv.dataset.categoryId = category.id;

                            categoryDiv.addEventListener('click', function () {
                                window.location.href = `/subcategories/${category.id}`;
                            });

                            categoryDiv.addEventListener('mouseenter', function () {
                                megaContent.querySelectorAll('.mega-category-item').forEach(c => c.classList.remove('active'));
                                this.classList.add('active');

                                subcategoriesColumn.style.display = 'block';

                                if (!allSubcategories[category.id]) {
                                    fetch(`/api/subcategories/${category.id}`)
                                        .then(r => r.json())
                                        .then(subcategories => {
                                            allSubcategories[category.id] = subcategories;
                                            displaySubcategories(subcategories, segment.name, category.name);
                                        });
                                } else {
                                    displaySubcategories(allSubcategories[category.id], segment.name, category.name);
                                }
                            });

                            categoriesList.appendChild(categoryDiv);
                        });
                    }
                });

                segmentsList.appendChild(segmentDiv);
            });

            function displaySubcategories(subcategories, segmentName, categoryName) {
                if (subcategories.length === 0) {
                    subcategoriesList.innerHTML = '<div class="mega-empty">No subcategories</div>';
                } else {
                    subcategoriesList.innerHTML = '';
                    subcategories.forEach(subcategory => {
                        const subcategoryLink = document.createElement('a');
                        subcategoryLink.className = 'mega-subcategory-item';
                        subcategoryLink.textContent = subcategory.name;

                        // Generate URL for product listing based on URL structure
                        const segSlug = segmentName.toLowerCase().replace(/[^a-z0-9]+/g, '-');
                        const catSlug = categoryName.toLowerCase().replace(/[^a-z0-9]+/g, '-');
                        const subSlug = subcategory.name.toLowerCase().replace(/[^a-z0-9]+/g, '-');
                        subcategoryLink.href = `/product-listing/${segSlug}/${catSlug}/${subSlug}`;

                        subcategoriesList.appendChild(subcategoryLink);
                    });
                }
            }

        });

    }).catch(error => {
        console.error('Error loading mega menu:', error);
        megaContents.forEach(megaContent => {
            megaContent.innerHTML = '<div class="mega-empty" style="color: #e74c3c;">Error loading menu</div>';
        });
    });
});
