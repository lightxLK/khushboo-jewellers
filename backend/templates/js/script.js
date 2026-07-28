// ===== KHUSHBOO JEWELLERS - COMPLETE UPDATED JAVASCRIPT =====
// 100% Based on Documentation - All 43 Changes Implemented

// ===== CONFIGURATION =====
const CONFIG = {
    carouselInterval: 2000, // Hero carousel - 2 seconds
    featuredCarouselInterval: 3000, // Faster featured products
    bannerCarouselInterval: 1000, // Banner rotation - 1 second
    scrollAnimationOffset: 0.85,
    bannerShowDelay: 3000
};

// ===== HEADER SCROLL EFFECT =====
const header = document.querySelector('.header');
let lastScrollY = 0;

window.addEventListener('scroll', () => {
    const currentScrollY = window.pageYOffset;

    if (currentScrollY > 100) {
        header.classList.add('scrolled');
    } else {
        header.classList.remove('scrolled');
    }

    lastScrollY = currentScrollY;
});

// ===== MOBILE MENU TOGGLE =====
const hamburger = document.getElementById('hamburger');
const navMenu = document.getElementById('navMenu');

if (hamburger && navMenu) {
    hamburger.addEventListener('click', () => {
        navMenu.classList.toggle('active');
        hamburger.classList.toggle('active');
    });

    // Close menu when clicking nav link
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', () => {
            navMenu.classList.remove('active');
            hamburger.classList.remove('active');
        });
    });

    // Close menu when clicking outside
    document.addEventListener('click', (e) => {
        if (!hamburger.contains(e.target) && !navMenu.contains(e.target)) {
            navMenu.classList.remove('active');
            hamburger.classList.remove('active');
        }
    });
}

// ===== SCROLL PROGRESS BAR =====
window.addEventListener('scroll', () => {
    const scrollProgress = document.querySelector('.scroll-progress-bar');
    if (scrollProgress) {
        const windowHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
        const scrolled = (window.pageYOffset / windowHeight) * 100;
        scrollProgress.style.width = scrolled + '%';
    }
});

// ===== HERO CAROUSEL - Change #1: Faster (3 seconds) =====
let currentSlide = 0;
const slides = document.querySelectorAll('.carousel-slide');
const dots = document.querySelectorAll('.dot');
const totalSlides = slides.length;

function showSlide(index) {
    // Remove active class from all
    slides.forEach(slide => slide.classList.remove('active'));
    dots.forEach(dot => dot.classList.remove('active'));

    // Add active to current
    if (slides[index]) slides[index].classList.add('active');
    if (dots[index]) dots[index].classList.add('active');
}

function nextSlide() {
    currentSlide = (currentSlide + 1) % totalSlides;
    showSlide(currentSlide);
}

function prevSlide() {
    currentSlide = (currentSlide - 1 + totalSlides) % totalSlides;
    showSlide(currentSlide);
}

// Change #2: Clickable carousel dots
dots.forEach((dot, index) => {
    dot.addEventListener('click', () => {
        currentSlide = index;
        showSlide(currentSlide);
        resetCarouselInterval();
    });
});

// Auto-rotate carousel - Change #1: 3 seconds interval
let carouselInterval = setInterval(nextSlide, CONFIG.carouselInterval);

function resetCarouselInterval() {
    clearInterval(carouselInterval);
    carouselInterval = setInterval(nextSlide, CONFIG.carouselInterval);
}

// Pause carousel on hover
const carouselContainer = document.querySelector('.carousel-container');
if (carouselContainer) {
    carouselContainer.addEventListener('mouseenter', () => {
        clearInterval(carouselInterval);
    });

    carouselContainer.addEventListener('mouseleave', () => {
        carouselInterval = setInterval(nextSlide, CONFIG.carouselInterval);
    });
}



// Redundant global banner code removed - initialized in master block at the bottom

// ===== SMOOTH SCROLLING FOR ANCHOR LINKS =====
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        const href = this.getAttribute('href');
        if (href === '#' || href === '#!') return;

        e.preventDefault();
        const target = document.querySelector(href);

        if (target) {
            const headerHeight = 89;
            const elementPosition = target.getBoundingClientRect().top;
            const offsetPosition = elementPosition + window.pageYOffset - headerHeight;

            window.scrollTo({
                top: offsetPosition,
                behavior: 'smooth'
            });
        }
    });
});

// ===== ACTIVE NAV LINK ON SCROLL =====
function updateActiveNavLink() {
    const sections = document.querySelectorAll('section[id]');
    const scrollY = window.pageYOffset;

    sections.forEach(section => {
        const sectionHeight = section.offsetHeight;
        const sectionTop = section.offsetTop - 150;
        const sectionId = section.getAttribute('id');
        const navLink = document.querySelector(`.nav-link[href="#${sectionId}"]`);

        if (scrollY > sectionTop && scrollY <= sectionTop + sectionHeight) {
            document.querySelectorAll('.nav-link').forEach(link => {
                link.classList.remove('active');
            });
            if (navLink) navLink.classList.add('active');
        }
    });
}

window.addEventListener('scroll', updateActiveNavLink);

// ===== FEATURED PRODUCTS CAROUSEL - Changes #20-21 =====
let featuredProducts = []; // Changed from const to let - will be populated dynamically

let currentFeaturedIndex = 2; // Start with center image

const featuredCenter = document.getElementById('featuredCenter');
const featuredLeft = document.getElementById('featuredLeft');
const featuredRight = document.getElementById('featuredRight');
const featuredPrev = document.getElementById('featuredPrev');
const featuredNext = document.getElementById('featuredNext');

function updateFeaturedCarousel() {
    // Safety check - don't run if no products loaded
    if (featuredProducts.length === 0) return;

    const leftIndex1 = (currentFeaturedIndex - 2 + featuredProducts.length) % featuredProducts.length;
    const leftIndex2 = (currentFeaturedIndex - 1 + featuredProducts.length) % featuredProducts.length;
    const centerIndex = currentFeaturedIndex;
    const rightIndex1 = (currentFeaturedIndex + 1) % featuredProducts.length;
    const rightIndex2 = (currentFeaturedIndex + 2) % featuredProducts.length;

    if (featuredCenter) {
        const centerImg = featuredCenter.querySelector('img');
        if (centerImg && featuredProducts[centerIndex]) {
            // Support both object {image: '...'} and string formats
            centerImg.src = featuredProducts[centerIndex].image || featuredProducts[centerIndex];
        }
    }

    if (featuredLeft) {
        const leftItems = featuredLeft.querySelectorAll('.featured-side-item');
        if (leftItems[0] && featuredProducts[leftIndex1]) {
            const img = leftItems[0].querySelector('img');
            if (img) img.src = featuredProducts[leftIndex1].image || featuredProducts[leftIndex1];
        }
        if (leftItems[1] && featuredProducts[leftIndex2]) {
            const img = leftItems[1].querySelector('img');
            if (img) img.src = featuredProducts[leftIndex2].image || featuredProducts[leftIndex2];
        }
    }

    if (featuredRight) {
        const rightItems = featuredRight.querySelectorAll('.featured-side-item');
        if (rightItems[0] && featuredProducts[rightIndex1]) {
            const img = rightItems[0].querySelector('img');
            if (img) img.src = featuredProducts[rightIndex1].image || featuredProducts[rightIndex1];
        }
        if (rightItems[1] && featuredProducts[rightIndex2]) {
            const img = rightItems[1].querySelector('img');
            if (img) img.src = featuredProducts[rightIndex2].image || featuredProducts[rightIndex2];
        }
    }
}

// ===== LOAD FEATURED PRODUCTS DYNAMICALLY FROM DATABASE =====
// ===== LOAD FEATURED PRODUCTS DYNAMICALLY FROM DATABASE =====
// REPLACE THE ENTIRE loadFeaturedProductsFromDB function with this:

async function loadFeaturedProductsFromDB() {
    try {
        console.log('🔄 Loading featured products from database...');

        // Wait for categories to be loaded
        let attempts = 0;
        while ((!allCategories || allCategories.length === 0) && attempts < 5) {
            console.log('⏳ Waiting for categories... attempt', attempts + 1);
            await new Promise(resolve => setTimeout(resolve, 500));
            attempts++;
        }

        if (!allCategories || allCategories.length === 0) {
            console.error('❌ Categories failed to load');
            useFallbackImages();
            return;
        }

        const mixedCategories = getMixedItems(allCategories, 10);
        featuredProducts = [];

        for (const category of mixedCategories) {
            if (featuredProducts.length >= 5) break;

            try {
                const response = await fetch(`/api/subcategories/${category.id}`);
                if (!response.ok) continue;

                const subcategories = await response.json();

                if (subcategories.length > 0) {
                    const randomSub = subcategories[Math.floor(Math.random() * subcategories.length)];

                    if (randomSub.image_path && randomSub.image_path !== '/images/placeholder.png') {
                        featuredProducts.push({
                            image: randomSub.image_path,
                            id: randomSub.id,
                            name: randomSub.name,
                            category: category.name
                        });
                    }
                }
            } catch (err) {
                console.warn('⚠️ Error fetching subcategories for category', category.id);
            }
        }

        console.log('✅ Featured products loaded:', featuredProducts.length);
        console.log('📸 Images:', featuredProducts.map(p => p.image));

        if (featuredProducts.length >= 5) {
            updateFeaturedCarousel();
        } else {
            console.warn('⚠️ Not enough products, using fallback');
            useFallbackImages();
        }

    } catch (error) {
        console.error('❌ Error loading featured products:', error);
        useFallbackImages();
    }
}

// ADD THIS NEW HELPER FUNCTION:
function useFallbackImages() {
    featuredProducts = [
        { image: '../images/featured-product-1.png', name: 'Featured 1' },
        { image: '../images/featured-product-2.png', name: 'Featured 2' },
        { image: '../images/featured-product-3.png', name: 'Featured 3' },
        { image: '../images/featured-product-4.png', name: 'Featured 4' },
        { image: '../images/featured-product-5.png', name: 'Featured 5' }
    ];
    updateFeaturedCarousel();
}

// Featured carousel will be initialized by loadFeaturedProductsFromDB()
// Don't call updateFeaturedCarousel() here - let it load data first

// ===== PARTNER LOGOS INFINITE SCROLL - Changes #22-23 =====
const partnersTrack = document.getElementById('partnersTrack');

if (partnersTrack) {
    const logos = partnersTrack.innerHTML;
    partnersTrack.innerHTML += logos; // Duplicate for seamless scroll
}

// ===== SCROLL ANIMATIONS - Change #5: Excessive but simple animations =====
function animateOnScroll() {
    const featureCards = document.querySelectorAll('.feature-card');
    featureCards.forEach((card, index) => {
        const cardTop = card.getBoundingClientRect().top;
        const triggerPoint = window.innerHeight * CONFIG.scrollAnimationOffset;

        if (cardTop < triggerPoint) {
            setTimeout(() => {
                card.classList.add('animate');
            }, index * 100);
        }
    });

    const timelineSteps = document.querySelectorAll('.timeline-step');
    timelineSteps.forEach((step, index) => {
        const stepTop = step.getBoundingClientRect().top;
        const triggerPoint = window.innerHeight * CONFIG.scrollAnimationOffset;

        if (stepTop < triggerPoint) {
            setTimeout(() => {
                step.classList.add('animate');
            }, index * 150);
        }
    });

    const wholesaleCards = document.querySelectorAll('.wholesale-card');
    wholesaleCards.forEach((card, index) => {
        const cardTop = card.getBoundingClientRect().top;
        const triggerPoint = window.innerHeight * CONFIG.scrollAnimationOffset;

        if (cardTop < triggerPoint) {
            setTimeout(() => {
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, index * 80);
        }
    });

    const testimonialCards = document.querySelectorAll('.testimonial-card');
    testimonialCards.forEach((card, index) => {
        const cardTop = card.getBoundingClientRect().top;
        const triggerPoint = window.innerHeight * CONFIG.scrollAnimationOffset;

        if (cardTop < triggerPoint) {
            setTimeout(() => {
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, index * 100);
        }
    });

    const dynamicCards = document.querySelectorAll('.dynamic-product-card');
    dynamicCards.forEach((card, index) => {
        const cardTop = card.getBoundingClientRect().top;
        const triggerPoint = window.innerHeight * CONFIG.scrollAnimationOffset;

        if (cardTop < triggerPoint) {
            setTimeout(() => {
                card.style.opacity = '1';
                card.style.transform = 'scale(1)';
            }, index * 60);
        }
    });
}

// DOMContentLoaded initialization moved to the master block at the bottom of the file

window.addEventListener('scroll', animateOnScroll);

// ===== STATS COUNTER ANIMATION =====
let statsAnimated = false;

function animateStats() {
    if (statsAnimated) return;

    const statsGrid = document.querySelector('.stats-grid');
    if (!statsGrid) return;

    const gridTop = statsGrid.getBoundingClientRect().top;
    const triggerPoint = window.innerHeight * 0.8;

    if (gridTop < triggerPoint) {
        statsAnimated = true;

        const statNumbers = document.querySelectorAll('.stat-number');
        statNumbers.forEach(stat => {
            const text = stat.textContent;
            let target, suffix = '';

            if (text.includes('+')) {
                target = parseInt(text.replace('+', ''));
                suffix = '+';
            } else if (text.includes('%')) {
                target = parseInt(text.replace('%', ''));
                suffix = '%';
            } else if (text.includes('/')) {
                return; // Skip 24/7 type stats
            } else {
                target = parseInt(text);
            }

            animateCounter(stat, 0, target, 2000, suffix);
        });
    }
}

function animateCounter(element, start, end, duration, suffix) {
    const range = end - start;
    const increment = range / (duration / 16);
    let current = start;

    const timer = setInterval(() => {
        current += increment;
        if (current >= end) {
            element.textContent = end + suffix;
            clearInterval(timer);
        } else {
            element.textContent = Math.floor(current) + suffix;
        }
    }, 16);
}

window.addEventListener('scroll', animateStats);

// ===== FIXED BANNER =====
const fixedBanner = document.getElementById('fixedBanner');
const closeBanner = document.getElementById('closeBanner');

setTimeout(() => {
    if (fixedBanner) {
        fixedBanner.classList.add('show');
    }
}, CONFIG.bannerShowDelay);

if (closeBanner && fixedBanner) {
    closeBanner.addEventListener('click', () => {
        fixedBanner.classList.remove('show');
        sessionStorage.setItem('bannerClosed', 'true');
    });
}

if (sessionStorage.getItem('bannerClosed') === 'true') {
    if (fixedBanner) {
        fixedBanner.style.display = 'none';
    }
}

// ===== CONTACT FORM VALIDATION =====
const contactForm = document.getElementById('contactForm');

if (contactForm) {
    contactForm.addEventListener('submit', function (e) {
        e.preventDefault();

        const name = document.getElementById('name');
        const email = document.getElementById('email');
        const phone = document.getElementById('phone');
        const message = document.getElementById('message');

        if (!name.value.trim()) {
            showError('Please enter your name');
            name.focus();
            return;
        }

        if (!email.value.trim()) {
            showError('Please enter your email');
            email.focus();
            return;
        }

        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(email.value)) {
            showError('Please enter a valid email address');
            email.focus();
            return;
        }

        if (!phone.value.trim()) {
            showError('Please enter your phone number');
            phone.focus();
            return;
        }

        const cleanPhone = phone.value.replace(/\D/g, '');
        if (cleanPhone.length < 10) {
            showError('Please enter a valid 10-digit phone number');
            phone.focus();
            return;
        }

        if (!message.value.trim()) {
            showError('Please enter your message');
            message.focus();
            return;
        }

        // Form is valid - will be submitted via existing HTML script
    });
}

function showError(msg) {
    alert(msg);
}

// ===== PREVENT DOUBLE FORM SUBMISSION =====
if (window.history.replaceState) {
    window.history.replaceState(null, null, window.location.href);
}

// ===== LAZY LOADING IMAGES =====
if ('IntersectionObserver' in window) {
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                if (img.dataset.src) {
                    img.src = img.dataset.src;
                    img.removeAttribute('data-src');
                    observer.unobserve(img);
                }
            }
        });
    }, {
        rootMargin: '50px'
    });

    const lazyImages = document.querySelectorAll('img[data-src]');
    lazyImages.forEach(img => imageObserver.observe(img));
}

// ===== PERFORMANCE OPTIMIZATION =====
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

const debouncedAnimateOnScroll = debounce(animateOnScroll, 50);
const debouncedAnimateStats = debounce(animateStats, 50);

window.removeEventListener('scroll', animateOnScroll);
window.removeEventListener('scroll', animateStats);
window.addEventListener('scroll', debouncedAnimateOnScroll);
window.addEventListener('scroll', debouncedAnimateStats);

// ===== SMOOTH ENTRANCE ANIMATIONS =====
// Entrance animations initialization moved to the master block at the bottom

// ===== KEYBOARD NAVIGATION =====
document.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft') {
        const activeCarousel = document.querySelector('.carousel-container:hover');
        if (activeCarousel) {
            prevSlide();
            resetCarouselInterval();
        }
    } else if (e.key === 'ArrowRight') {
        const activeCarousel = document.querySelector('.carousel-container:hover');
        if (activeCarousel) {
            nextSlide();
            resetCarouselInterval();
        }
    }
});

// ===== CONSOLE BRANDING =====
console.log(
    '%c🪙 Khushboo Jewellers',
    'color: #C9A961; font-size: 24px; font-weight: bold; text-shadow: 2px 2px 4px rgba(0,0,0,0.2);'
);
console.log(
    '%c✨ Odisha\'s Traditional Silver Wholesale Partner Since 2002',
    'color: #6B5D4F; font-size: 14px; font-weight: 500;'
);
console.log(
    '%c📍 Nayasadak, Cuttack | 📞 +91 78735 90001',
    'color: #95A5A6; font-size: 12px;'
);
console.log(
    '%c💎 925 Sterling Silver | BIS Certified | 500+ Retail Partners',
    'color: #5C4033; font-size: 11px; font-style: italic;'
);

// ===== SCROLL ANIMATIONS - SLIDE IN FROM LEFT (HERITAGE) ===== 
function initSlideInAnimation() {
    const slideInItems = document.querySelectorAll('.slide-in-item');

    const slideInObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const delay = entry.target.dataset.delay || 0;
                setTimeout(() => {
                    entry.target.classList.add('slide-in-active');
                }, delay);
                slideInObserver.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.2
    });

    slideInItems.forEach(item => slideInObserver.observe(item));
}

// ===== POP OUT ANIMATION (MISSION/VISION/VALUES) =====
function initPopOutAnimation() {
    const popOutCards = document.querySelectorAll('.pop-out-card');

    const popOutObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const delay = entry.target.dataset.delay || 0;
                setTimeout(() => {
                    entry.target.classList.add('pop-out-active');
                }, delay);
                popOutObserver.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.2
    });

    popOutCards.forEach(card => popOutObserver.observe(card));
}

// ===== GLOWING COUNTERS ANIMATION =====
function animateCounter(element, start, end, duration, suffix) {
    const range = end - start;
    const increment = range / (duration / 16);
    let current = start;

    const timer = setInterval(() => {
        current += increment;

        // ADD GLOW EFFECT WHILE COUNTING
        element.classList.add('glow-active');

        if (current >= end) {
            element.textContent = end + suffix;
            clearInterval(timer);
            // REMOVE GLOW WHEN DONE
            setTimeout(() => {
                element.classList.remove('glow-active');
            }, 300);
        } else {
            element.textContent = Math.floor(current) + suffix;
        }
    }, 16);
}

// INITIALIZE ALL ANIMATIONS ON PAGE LOAD
// Animation initialization moved to the master block at the bottom

// ===== CONTACT FORM POPUP FUNCTIONS =====
function showThankYouPopup() {
    // Create popup overlay
    const overlay = document.createElement('div');
    overlay.className = 'popup-overlay';

    const popup = document.createElement('div');
    popup.className = 'popup-content';
    popup.innerHTML = `
        <div class="popup-icon">✅</div>
        <h2>Thank You!</h2>
        <p>Your message has been sent successfully.<br>We will contact you soon.</p>
        <button class="popup-btn" onclick="closeThankYouPopup()">OK</button>
    `;

    overlay.appendChild(popup);
    document.body.appendChild(overlay);

    // Trigger animation
    setTimeout(() => {
        overlay.classList.add('show');
    }, 10);
}

function closeThankYouPopup() {
    const overlay = document.querySelector('.popup-overlay');
    if (overlay) {
        overlay.classList.remove('show');
        setTimeout(() => {
            overlay.remove();
        }, 300);
    }
}

// ========================================
// ===== NEW SECTIONS JAVASCRIPT =====
// ===== Added: January 2026 =====
// ========================================

// ===== GLOBAL DATA STORAGE =====
let allSegments = [];
let allCategories = [];
let allSubcategories = [];

// ===== HOVER SLIDESHOW FOR GALLERY IMAGES =====
function attachHoverSlideshow(cardElement, primaryImage, galleryImages) {
    if (!galleryImages || galleryImages.length === 0) return;
    if (!primaryImage) return;

    const imgEl = cardElement.querySelector('img');
    if (!imgEl) return;

    const allImages = [primaryImage, ...galleryImages.filter(Boolean)];
    if (allImages.length < 2) return;

    let hoverInterval = null;
    let currentIndex = 0;

    cardElement.addEventListener('mouseenter', () => {
        currentIndex = 1;
        imgEl.src = allImages[currentIndex];
        hoverInterval = setInterval(() => {
            currentIndex = (currentIndex + 1) % allImages.length;
            imgEl.src = allImages[currentIndex];
        }, 700);
    });

    cardElement.addEventListener('mouseleave', () => {
        clearInterval(hoverInterval);
        hoverInterval = null;
        currentIndex = 0;
        imgEl.src = primaryImage;
    });
}
// ===== END HOVER SLIDESHOW =====

// ===== IMAGE HOVER SWAP HELPER FUNCTION =====
function attachImageSwap(cardElement, primaryImage, secondaryImage) {
    if (!cardElement || !primaryImage) return;

    const img = cardElement.querySelector('img');
    if (!img) return;

    // Store both images as data attributes
    img.dataset.primary = primaryImage;
    img.dataset.secondary = secondaryImage || primaryImage;

    // Set primary as default
    img.src = primaryImage;

    // Add hover listeners
    cardElement.addEventListener('mouseenter', () => {
        if (img.dataset.secondary && img.dataset.secondary !== img.dataset.primary) {
            img.src = img.dataset.secondary;
        }
    });

    cardElement.addEventListener('mouseleave', () => {
        img.src = img.dataset.primary;
    });
}

// ===== FETCH ALL DATA ON PAGE LOAD =====
async function fetchAllData() {
    try {
        console.log('📡 Fetching all data...');

        // Fetch segments
        const segmentsResponse = await fetch('/api/segments');
        allSegments = await segmentsResponse.json();
        console.log('✅ Segments loaded:', allSegments.length);

        // Fetch categories
        const categoriesResponse = await fetch('/api/categories');
        allCategories = await categoriesResponse.json();

        // ✅ FIX: Add segment_name to each category
        allCategories = allCategories.map(cat => {
            const segment = allSegments.find(seg => seg.id === cat.segment_id);
            return {
                ...cat,
                segment_name: segment ? segment.name : 'All'
            };
        });

        console.log('✅ Categories loaded:', allCategories.length);
        console.log('🔍 Sample category:', allCategories[0]);

    } catch (error) {
        console.error('❌ Error fetching data:', error);
    }
}

// ===== MIXING HELPER FUNCTIONS =====
function shuffleArray(array) {
    const shuffled = [...array];
    for (let i = shuffled.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    return shuffled;
}

function getMixedItems(items, count, segmentKey = 'segment_id') {
    if (!items || items.length === 0) return [];

    // Group items by segment
    const bySegment = {};
    items.forEach(item => {
        const segmentId = item[segmentKey];
        if (!bySegment[segmentId]) bySegment[segmentId] = [];
        bySegment[segmentId].push(item);
    });

    // Pick items evenly from each segment
    const mixed = [];
    const segmentIds = Object.keys(bySegment);
    let index = 0;

    while (mixed.length < count && segmentIds.length > 0) {
        const currentSegment = segmentIds[index % segmentIds.length];
        const segmentItems = bySegment[currentSegment];

        if (segmentItems && segmentItems.length > 0) {
            const randomItem = segmentItems.splice(
                Math.floor(Math.random() * segmentItems.length),
                1
            )[0];
            mixed.push(randomItem);
        }

        if (bySegment[currentSegment].length === 0) {
            segmentIds.splice(segmentIds.indexOf(currentSegment), 1);
        }

        index++;
    }

    return shuffleArray(mixed);
}

// ===== SECTION 3: MARQUEE CATEGORY SLIDER =====
async function populateMarqueeSlider() {
    const marqueeTrack = document.getElementById('marqueeTrack');
    if (!marqueeTrack) return;

    try {
        console.log('🎠 Populating marquee slider...');

        // Get mixed categories from all segments
        const mixedCategories = getMixedItems(allCategories, 20);

        if (mixedCategories.length === 0) {
            console.warn('⚠️ No categories available for marquee');
            return;
        }

        // Create marquee items
        mixedCategories.forEach(category => {
            const item = document.createElement('a');
            item.className = 'marquee-item';
            item.href = `/subcategories/${category.id}`;

            const imagePath = category.image_path || '/images/placeholder.png';

            item.innerHTML = `
                <div class="marquee-image">
                    <img src="${imagePath}" alt="${category.name}">
                </div>
                <div class="marquee-name">${category.name}</div>
            `;

            marqueeTrack.appendChild(item);
        });

        // Duplicate multiple times for a truly seamless infinite scroll
        const originalContent = marqueeTrack.innerHTML;
        marqueeTrack.innerHTML = originalContent + originalContent + originalContent;

        console.log('✅ Marquee slider populated with', mixedCategories.length, 'items');

    } catch (error) {
        console.error('❌ Error populating marquee:', error);
    }
}

// ===== CREATE PRODUCT CARD HELPER =====
function createProductCard(product, type = 'subcategory') {
    const card = document.createElement('a');
    card.className = 'product-grid-item';

    const segSlug = (product.segment_name || 'all').toLowerCase().replace(/\s+/g, '-');
    const catSlug = (product.category_name || 'all').toLowerCase().replace(/\s+/g, '-');
    const subSlug = (product.name || 'product').toLowerCase().replace(/\s+/g, '-');

    if (type === 'subcategory') {
        card.href = `/product-listing/${product.id}`;
    } else if (type === 'product') {
        const subcatSlug = (product.subcategory_name || subSlug).toLowerCase().replace(/\s+/g, '-');
        const prodSlug = (product.name || 'product').toLowerCase().replace(/\s+/g, '-');
        card.href = `/product/${segSlug}/${catSlug}/${subcatSlug}/${prodSlug}/${product.id}`;
    }

    const primaryImage = product.image_path || product.primary_image || '/images/placeholder.png';
    const secondaryImage = product.secondary_image || product.image_path_2 || primaryImage;

    card.innerHTML = `
        <div class="product-grid-image">
            <img src="${primaryImage}" alt="${product.name}">
        </div>
        <div class="product-grid-info">
            <div class="product-grid-name">${product.name}</div>
        </div>
    `;

    // ✅ ATTACH IMAGE SWAP
    attachImageSwap(card, primaryImage, secondaryImage);

    return card;
}

// ===== SECTION 7: PRODUCT GRID - 8 PRODUCTS =====
async function populateProductGrid8() {
    const grid = document.getElementById('productGrid8');
    if (!grid) return;

    try {
        console.log('📦 Populating product grid 8...');

        const products = [];
        const mixedCategories = getMixedItems(allCategories, 8);

        for (const category of mixedCategories) {
            try {
                const subcategoriesResponse = await fetch(`/api/subcategories/${category.id}`);
                const subcategories = await subcategoriesResponse.json();

                if (subcategories.length > 0) {
                    const randomSub = subcategories[Math.floor(Math.random() * subcategories.length)];
                    products.push({
                        ...randomSub,
                        segment_name: category.segment_name,
                        category_name: category.name
                    });
                }
            } catch (err) {
                console.warn('⚠️ Error fetching subcategories for category', category.id);
            }
        }

        products.slice(0, 8).forEach(product => {
            const card = document.createElement('a');
            card.className = 'product-grid-item';

            const segSlug = (product.segment_name || 'all').toLowerCase().replace(/\s+/g, '-');
            const catSlug = (product.category_name || 'all').toLowerCase().replace(/\s+/g, '-');
            const subSlug = (product.name || 'product').toLowerCase().replace(/\s+/g, '-');

            card.href = `/product-listing/${product.id}`;

            const primaryImage = product.image_path || '/images/placeholder.png';
            const secondaryImage = product.secondary_image || product.image_path_2 || primaryImage;

            card.innerHTML = `
        <div class="product-grid-image">
            <img src="${primaryImage}" alt="${product.name}">
        </div>
        <div class="product-grid-info">
            <div class="product-grid-name">${product.name}</div>
        </div>
    `;

            // ✅ ATTACH IMAGE SWAP
            attachImageSwap(card, primaryImage, secondaryImage);

            grid.appendChild(card);
        });

        console.log('✅ Product grid 8 populated with', products.length, 'items');

    } catch (error) {
        console.error('❌ Error populating product grid:', error);
    }
}

// ===== SECTION 8: 4-BANNER LIFESTYLE GRID =====
async function populateLifestyleBanners() {
    const grid = document.getElementById('lifestyleGrid');
    if (!grid) return;

    try {
        console.log('🖼️ Populating lifestyle banners...');

        const mixedCategories = getMixedItems(allCategories, 4);

        if (mixedCategories.length === 0) {
            console.warn('⚠️ No categories available for lifestyle banners');
            return;
        }

        mixedCategories.forEach(category => {
            const card = document.createElement('a');
            card.className = 'category-card';
            card.href = `/subcategories/${category.id}`;

            const primaryImage = category.image_path || '/images/placeholder.png';
            const secondaryImage = category.secondary_image || category.image_path_2 || primaryImage;

            card.innerHTML = `
        <img src="${primaryImage}" alt="${category.name}">
        <div class="category-overlay">
            <h3>${category.name}</h3>
        </div>
    `;

            // ✅ ATTACH IMAGE SWAP
            attachImageSwap(card, primaryImage, secondaryImage);

            grid.appendChild(card);
        });

        console.log('✅ Lifestyle banners populated with', mixedCategories.length, 'items');

    } catch (error) {
        console.error('❌ Error populating lifestyle banners:', error);
    }
}

// ===== SECTION 11: 6-GRID CATEGORY SHOWCASE =====
async function populateCategoryGrid6() {
    const grid = document.getElementById('categoryGrid6');
    if (!grid) return;

    try {
        console.log('🎨 Populating category grid 6...');

        const mixedCategories = getMixedItems(allCategories, 6);

        if (mixedCategories.length === 0) {
            console.warn('⚠️ No categories available for grid 6');
            return;
        }

        mixedCategories.forEach(category => {
            const card = document.createElement('a');
            card.className = 'category-card';
            card.href = `/subcategories/${category.id}`;

            const primaryImage = category.image_path || '/images/placeholder.png';
            const secondaryImage = category.secondary_image || category.image_path_2 || primaryImage;

            card.innerHTML = `
        <img src="${primaryImage}" alt="${category.name}">
        <div class="category-overlay">
            <h3>${category.name}</h3>
        </div>
    `;

            // ✅ ATTACH IMAGE SWAP
            attachImageSwap(card, primaryImage, secondaryImage);

            grid.appendChild(card);
        });

        console.log('✅ Category grid 6 populated with', mixedCategories.length, 'items');

    } catch (error) {
        console.error('❌ Error populating category grid 6:', error);
    }
}

// ===== SECTION 12: PRODUCT GRID - COMBOS =====
async function populateProductGridCombos() {
    const grid = document.getElementById('productGridCombos');
    if (!grid) return;

    try {
        console.log('🎁 Populating combos grid...');

        const products = [];
        const mixedCategories = getMixedItems(allCategories, 8);

        for (const category of mixedCategories) {
            try {
                const subcategoriesResponse = await fetch(`/api/subcategories/${category.id}`);
                const subcategories = await subcategoriesResponse.json();

                if (subcategories.length > 0) {
                    const randomSub = subcategories[Math.floor(Math.random() * subcategories.length)];
                    products.push({
                        ...randomSub,
                        segment_name: category.segment_name,
                        category_name: category.name
                    });
                }
            } catch (err) {
                console.warn('⚠️ Error fetching subcategories for combos');
            }
        }

        shuffleArray(products).slice(0, 8).forEach(product => {
            const card = createProductCard(product, 'subcategory');
            grid.appendChild(card);
        });

        console.log('✅ Combos grid populated with', products.length, 'items');

    } catch (error) {
        console.error('❌ Error populating combos grid:', error);
    }
}

// ===== PRODUCT CAROUSEL CLASS =====
class ProductCarousel {
    constructor(containerId, prevBtnId, nextBtnId, paginationId = null) {
        this.container = document.getElementById(containerId);
        this.prevBtn = document.getElementById(prevBtnId);
        this.nextBtn = document.getElementById(nextBtnId);
        this.paginationContainer = paginationId ? document.getElementById(paginationId) : null;

        this.currentIndex = 0;
        this.itemsPerPage = 4;
        this.products = [];

        this.init();
    }

    init() {
        if (!this.container) return;

        // ✅ CRITICAL FIX: Force arrows visible and clickable
        if (this.prevBtn) {
            this.prevBtn.style.cursor = 'pointer';
            this.prevBtn.style.pointerEvents = 'auto';
            this.prevBtn.style.background = 'white';
            this.prevBtn.style.zIndex = '9999';
            this.prevBtn.style.opacity = '1';
            this.prevBtn.style.visibility = 'visible';
            this.prevBtn.style.display = 'flex';

            this.prevBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('✅ Prev clicked - Index was:', this.currentIndex);
                this.prev();
                console.log('✅ Prev clicked - Index now:', this.currentIndex);
            });
        }

        if (this.nextBtn) {
            this.nextBtn.style.cursor = 'pointer';
            this.nextBtn.style.pointerEvents = 'auto';
            this.nextBtn.style.background = 'white';
            this.nextBtn.style.zIndex = '9999';
            this.nextBtn.style.opacity = '1';
            this.nextBtn.style.visibility = 'visible';
            this.nextBtn.style.display = 'flex';

            this.nextBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('✅ Next clicked - Index was:', this.currentIndex);
                this.next();
                console.log('✅ Next clicked - Index now:', this.currentIndex);
            });
        }
    }

    async loadProducts(count = 16) {
        try {
            const mixedCategories = getMixedItems(allCategories, count);

            for (const category of mixedCategories) {
                try {
                    const subcategoriesResponse = await fetch(`/api/subcategories/${category.id}`);
                    const subcategories = await subcategoriesResponse.json();

                    if (subcategories.length > 0) {
                        const randomSub = subcategories[Math.floor(Math.random() * subcategories.length)];

                        // ✅ FIX: Clearly mark this as a subcategory, not a product
                        this.products.push({
                            ...randomSub,
                            segment_name: category.segment_name || 'all',
                            category_name: category.name || 'all',
                            subcategory_name: randomSub.name, // ✅ ADD THIS
                            item_type: 'subcategory' // ✅ ADD THIS FLAG
                        });
                    }
                } catch (err) {
                    console.warn('⚠️ Error loading carousel products');
                }
            }

            this.render();
            this.createPagination();

        } catch (error) {
            console.error('❌ Error loading carousel products:', error);
        }
    }

    render() {
        if (!this.container) return;

        this.container.innerHTML = '';

        const startIndex = this.currentIndex * this.itemsPerPage;
        const endIndex = startIndex + this.itemsPerPage;
        const visibleProducts = this.products.slice(startIndex, endIndex);

        visibleProducts.forEach(product => {
            const card = document.createElement('a');
            card.className = 'product-grid-item';

            const segSlug = (product.segment_name || 'all').toLowerCase().replace(/\s+/g, '-');
            const catSlug = (product.category_name || 'all').toLowerCase().replace(/\s+/g, '-');
            const subSlug = (product.name || 'product').toLowerCase().replace(/\s+/g, '-');

            card.href = `/product-listing/${product.id}`;

            const primaryImage = product.image_path || '/images/placeholder.png';
            const secondaryImage = product.secondary_image || product.image_path_2 || primaryImage;

            card.innerHTML = `
            <div class="product-grid-image">
                <img src="${primaryImage}" alt="${product.name}">
            </div>
            <div class="product-grid-info">
                <div class="product-grid-name">${product.name}</div>
            </div>
        `;

            // ✅ ATTACH IMAGE SWAP
            attachImageSwap(card, primaryImage, secondaryImage);

            this.container.appendChild(card);
        });
    }

    createPagination() {
        if (!this.paginationContainer) return;

        this.paginationContainer.innerHTML = '';

        const totalPages = Math.ceil(this.products.length / this.itemsPerPage);

        for (let i = 0; i < totalPages; i++) {
            const dot = document.createElement('span');
            dot.className = 'pagination-dot';
            if (i === this.currentIndex) dot.classList.add('active');

            dot.addEventListener('click', () => {
                this.currentIndex = i;
                this.render();
                this.updatePagination();
            });

            this.paginationContainer.appendChild(dot);
        }
    }

    updatePagination() {
        if (!this.paginationContainer) return;

        const dots = this.paginationContainer.querySelectorAll('.pagination-dot');
        dots.forEach((dot, index) => {
            dot.classList.toggle('active', index === this.currentIndex);
        });
    }

    next() {
        const totalPages = Math.ceil(this.products.length / this.itemsPerPage);
        this.currentIndex = (this.currentIndex + 1) % totalPages;
        this.render();
        this.updatePagination();
    }

    prev() {
        const totalPages = Math.ceil(this.products.length / this.itemsPerPage);
        this.currentIndex = (this.currentIndex - 1 + totalPages) % totalPages;
        this.render();
        this.updatePagination();
    }
}

// ===== INITIALIZE CAROUSELS =====
let carousel1, carousel2, carousel3;

async function initializeCarousels() {
    console.log('🎪 Initializing carousels...');

    try {
        // Section 9: Product Carousel 1
        carousel1 = new ProductCarousel('productCarousel1', 'carouselPrev1', 'carouselNext1');
        carousel1.itemsPerPage = 4;
        await carousel1.loadProducts(16);
        console.log('✅ Carousel 1 initialized');

        // Section 13: Product Carousel 2 (with pagination)
        carousel2 = new ProductCarousel('productCarousel2', 'carouselPrev2', 'carouselNext2', 'pagination2');
        await carousel2.loadProducts(8);
        console.log('✅ Carousel 2 initialized');

        // Section 15: Product Carousel 3
        carousel3 = new ProductCarousel('productCarousel3', 'carouselPrev3', 'carouselNext3');
        carousel3.itemsPerPage = 4;
        await carousel3.loadProducts(16);
        console.log('✅ Carousel 3 initialized');

    } catch (error) {
        console.error('❌ Error initializing carousels:', error);
    }
}

// ===== POPULATE EXCLUSIVE DEALS 4-GRID =====
async function populateExclusiveDualScroll() {
    const row1 = document.getElementById('exclusiveRow1');
    const row2 = document.getElementById('exclusiveRow2');
    if (!row1 || !row2) return;

    try {
        console.log('🎁 Populating exclusive dual scroll...');

        // Fetch enough products for both rows
        const products = [];
        const mixedCategories = getMixedItems(allCategories, 20);

        for (const category of mixedCategories) {
            try {
                const res = await fetch(`/api/subcategories/${category.id}`);
                const subs = await res.json();
                subs.forEach(sub => {
                    products.push({
                        ...sub,
                        segment_name: category.segment_name,
                        category_name: category.name
                    });
                });
            } catch (err) { }
            if (products.length >= 20) break;
        }

        if (products.length === 0) return;

        // Split into two groups
        const shuffled = shuffleArray(products);
        const row1Items = shuffled.slice(0, 10);
        const row2Items = shuffled.slice(10, 20).length > 0 ? shuffled.slice(10, 20) : shuffleArray(products).slice(0, 10);

        // Helper to create one card
        function createScrollCard(product) {
            const card = document.createElement('a');
            card.className = 'exclusive-scroll-card';

            card.href = `/product-listing/${product.id}`;

            const primary = product.image_path || '/images/placeholder.png';
            // secondary_image if API provides it, otherwise use primary (no swap if missing)
            const secondary = product.secondary_image || product.image_path || primary;

            card.innerHTML = `
                <div class="exclusive-scroll-img-wrap">
                    <img src="${primary}" alt="${product.name}" data-primary="${primary}" data-secondary="${secondary}">
                </div>
                <div class="exclusive-scroll-name">${product.name}</div>
            `;

            // Hover swap logic
            const img = card.querySelector('img');
            card.addEventListener('mouseenter', () => {
                img.src = img.dataset.secondary;
            });
            card.addEventListener('mouseleave', () => {
                img.src = img.dataset.primary;
            });

            return card;
        }

        // Fill Row 1
        row1Items.forEach(p => row1.appendChild(createScrollCard(p)));
        // Duplicate for seamless loop
        row1.innerHTML += row1.innerHTML;

        // Fill Row 2
        row2Items.forEach(p => row2.appendChild(createScrollCard(p)));
        // Duplicate for seamless loop
        row2.innerHTML += row2.innerHTML;

        // Re-attach hover events after innerHTML duplication
        row1.querySelectorAll('.exclusive-scroll-card').forEach(card => {
            const img = card.querySelector('img');
            card.addEventListener('mouseenter', () => { img.src = img.dataset.secondary; });
            card.addEventListener('mouseleave', () => { img.src = img.dataset.primary; });
        });
        row2.querySelectorAll('.exclusive-scroll-card').forEach(card => {
            const img = card.querySelector('img');
            card.addEventListener('mouseenter', () => { img.src = img.dataset.secondary; });
            card.addEventListener('mouseleave', () => { img.src = img.dataset.primary; });
        });

        console.log('✅ Exclusive dual scroll populated');
    } catch (error) {
        console.error('❌ Error populating exclusive dual scroll:', error);
    }
}

// ===== CURVED BANNER RIGHT PANEL - 4 RANDOM PRODUCTS =====
async function populateBannerProducts() {
    const grid = document.getElementById('bannerProductGrid');
    if (!grid) return;

    // Clear grid first (Safety)
    grid.innerHTML = '';

    try {
        console.log('💎 Populating banner products grid (max 4)...');
        const mixedCategories = shuffleArray([...allCategories]);
        const products = [];

        for (const category of mixedCategories) {
            if (products.length >= 4) break;
            try {
                const res = await fetch(`/api/subcategories/${category.id}`);
                const subs = await res.json();
                if (subs && subs.length > 0) {
                    const randomSub = subs[Math.floor(Math.random() * subs.length)];
                    if (randomSub.image_path && randomSub.image_path !== '/images/placeholder.png') {
                        products.push({
                            ...randomSub,
                            segment_name: category.segment_name,
                            category_name: category.name
                        });
                    }
                }
            } catch (err) { }
        }

        // Final safety: ensure exactly 4 or less, and clear again just in case of race conditions
        grid.innerHTML = '';
        products.slice(0, 4).forEach(product => {
            const card = document.createElement('a');
            card.className = 'banner-product-card';
            card.href = `/product-listing/${product.id}`;
            const img = product.image_path || '/images/placeholder.png';
            card.innerHTML = `
                <div class="banner-product-img">
                    <img src="${img}" alt="${product.name}">
                </div>
                <div class="banner-product-name">${product.name}</div>
            `;
            grid.appendChild(card);
        });

        console.log(`✅ Banner products populated: ${products.length} items`);

    } catch (error) {
        console.error('❌ Error populating banner products:', error);
    }
}

// ===== MASTER INITIALIZATION FUNCTION =====
async function initializeNewSections() {
    console.log('🚀 ========================================');
    console.log('🚀 INITIALIZING NEW SECTIONS...');
    console.log('🚀 ========================================');

    try {
        // Step 1: Fetch all data
        await fetchAllData();

        // Step 2: Populate all new sections
        await Promise.all([
            populateMarqueeSlider(),
            populateProductGrid8(),
            populateLifestyleBanners(),
            populateCategoryGrid6(),
            populateProductGridCombos(),
            populateExclusiveDualScroll(),
            populateBannerProducts(),
        ]);

        // Step 3: Initialize carousels
        await initializeCarousels();        // Sections 9, 13, 15

        console.log('✅ ========================================');
        console.log('✅ ALL NEW SECTIONS INITIALIZED!');
        console.log('✅ ========================================');

    } catch (error) {
        console.error('❌ ========================================');
        console.error('❌ ERROR INITIALIZING NEW SECTIONS:', error);
        console.error('❌ ========================================');
    }
}

// Redundant listener removed - logic moved to master block

// ========================================
// ===== END OF NEW SECTIONS CODE =====
// ========================================

// ===== POPULATE FOOTER CATEGORIES DYNAMICALLY =====
async function populateFooterCategories() {
    const footerCategoriesList = document.getElementById('footerCategories');
    if (!footerCategoriesList) return;

    try {
        console.log('📂 Populating footer categories...');

        // Use existing allSegments if available, otherwise fetch
        let segments = allSegments;
        if (!segments || segments.length === 0) {
            const response = await fetch('/api/segments');
            segments = await response.json();
        }

        footerCategoriesList.innerHTML = '';

        // Take first 6 segments
        const displaySegments = segments.slice(0, 6);

        displaySegments.forEach(segment => {
            const li = document.createElement('li');
            const a = document.createElement('a');
            a.href = `/categories/${segment.id}`;
            a.textContent = segment.name;
            li.appendChild(a);
            footerCategoriesList.appendChild(li);
        });

        console.log('✅ Footer categories populated');
    } catch (error) {
        console.error('❌ Error populating footer categories:', error);
        footerCategoriesList.innerHTML = '<li><a href="#collections">View All</a></li>';
    }
}

// ===== NEWSLETTER FORM HANDLER =====
// Newsletter and footer initialization moved to master block

// ===== BANNER CAROUSEL FIX - BOTH SECTIONS =====
// This handles BOTH the Curved Banners (4 images) AND Signature Collection (3 images)

// Banner carousel initialization moved to master block

function initBannerCarousel(sectionSelector, rotationInterval) {
    const section = document.querySelector(sectionSelector);
    if (!section) {
        console.warn(`⚠️ Section not found: ${sectionSelector}`);
        return;
    }

    const slides = section.querySelectorAll('.banner-slide');
    const dots = section.querySelectorAll('.banner-dot');
    const carousel = section.querySelector('.banners-carousel');

    if (slides.length === 0) {
        console.warn(`⚠️ No slides found in ${sectionSelector}`);
        return;
    }

    let currentIndex = 0;
    let autoRotateInterval;

    console.log(`✅ Found ${slides.length} slides in ${sectionSelector}`);

    // Function to show specific slide with SLOWER transition
    function showSlide(index) {
        // Remove active from all slides and dots
        slides.forEach(slide => {
            slide.classList.remove('active');
            slide.style.opacity = '0';
            slide.style.transition = 'opacity 1.5s ease-in-out'; /* SLOWER */
        });
        dots.forEach(dot => dot.classList.remove('active'));

        // Add active to current slide and dot
        if (slides[index]) {
            slides[index].classList.add('active');
            slides[index].style.opacity = '1';
            slides[index].style.zIndex = '2';
        }

        if (dots[index]) {
            dots[index].classList.add('active');
        }

        console.log(`📍 Showing slide ${index + 1}/${slides.length} in ${sectionSelector}`);
    }

    // Function to go to next slide
    function nextSlide() {
        currentIndex = (currentIndex + 1) % slides.length;
        showSlide(currentIndex);
    }

    // Function to go to previous slide
    function prevSlide() {
        currentIndex = (currentIndex - 1 + slides.length) % slides.length;
        showSlide(currentIndex);
    }

    // Auto-rotation with SLOWER interval
    function startAutoRotate() {
        autoRotateInterval = setInterval(nextSlide, rotationInterval);
    }

    function stopAutoRotate() {
        clearInterval(autoRotateInterval);
    }

    function resetAutoRotate() {
        stopAutoRotate();
        startAutoRotate();
    }

    // Click handlers for dots
    dots.forEach((dot, index) => {
        dot.addEventListener('click', function () {
            console.log(`🖱️ Dot ${index + 1} clicked in ${sectionSelector}`);
            currentIndex = index;
            showSlide(currentIndex);
            resetAutoRotate();

            // Pause for 10 seconds after manual click (LONGER)
            stopAutoRotate();
            setTimeout(() => {
                startAutoRotate();
            }, 10000);
        });

        dot.style.cursor = 'pointer';
    });

    // Pause on hover
    if (carousel) {
        carousel.addEventListener('mouseenter', () => {
            stopAutoRotate();
            console.log(`⏸️ Paused rotation in ${sectionSelector}`);
        });

        carousel.addEventListener('mouseleave', () => {
            startAutoRotate();
            console.log(`▶️ Resumed rotation in ${sectionSelector}`);
        });
    }

    // Initialize
    showSlide(0);
    startAutoRotate();

    console.log(`✅ Banner carousel initialized: ${sectionSelector}`);
    console.log(`   - ${slides.length} slides`);
    console.log(`   - Rotation: ${rotationInterval}ms (SLOWER)`);
}




// ========================================
// ===== MASTER INITIALIZATION BLOCK =====
// ========================================
document.addEventListener('DOMContentLoaded', () => {
    console.log('🏁 Starting Master Initialization...');

    // 1. Initial State for Animations
    document.querySelectorAll('.wholesale-card, .testimonial-card').forEach(element => {
        element.style.opacity = '0';
        element.style.transform = 'translateY(30px)';
        element.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
    });

    document.querySelectorAll('.dynamic-product-card').forEach(element => {
        element.style.opacity = '0';
        element.style.transform = 'scale(0.95)';
        element.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
    });

    // 2. Entrance Observers
    const observerOptions = { threshold: 0.1, rootMargin: '0px 0px -50px 0px' };
    const fadeInObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);

    document.querySelectorAll('.section-header').forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = 'opacity 0.8s ease, transform 0.8s ease';
        fadeInObserver.observe(el);
    });

    // 3. Static Section Initialization
    initSlideInAnimation();
    initPopOutAnimation();
    animateOnScroll();

    // 4. Banner Carousels
    console.log('🎯 Initializing banner carousels...');
    initBannerCarousel('.curved-banners:not(.signature-banners)', 2000);
    initBannerCarousel('.signature-banners', 1000);

    // 5. Dynamic Data & Section Population
    loadFeaturedProductsFromDB();
    initializeNewSections(); // This calls fetchAllData internally
    populateFooterCategories();

    // 6. Form Handlers
    const newsletterForm = document.getElementById('newsletterForm');
    if (newsletterForm) {
        newsletterForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const email = this.querySelector('input[type="email"]').value;
            alert('✅ Thank you for subscribing!\n\nWe\'ll send updates to: ' + email);
            this.reset();
        });
    }

    console.log('🏁 Master Initialization Complete.');
});

// ===== END OF JAVASCRIPT FILE =====//
