document.addEventListener('alpine:init', () => {
    Alpine.data('navbar', function() {
        return {
            isModalOpen: false,
            isMobileSelectorOpen: false,
            isPopoverOpen: false,
            debouncedSearch: '',
            debounceTimer: null,
            currentLocalitySlug: '',
            currentLocalityName: '',
            currentLocalityNamePrepositional: '',
            selectedDistrict: null,
            highlightedIndex: null,
            localities: [],
            
            // Getters и Setters
            get searchQuery() {
                return this.debouncedSearch;
            },
            set searchQuery(value) {
                clearTimeout(this.debounceTimer);
                this.debounceTimer = setTimeout(() => {
                    this.debouncedSearch = value;
                }, 300);
            },
            
            // Методы
            getNewPath(localitySlug) {
                const currentPath = window.location.pathname;
                const currentSlug = this.currentLocalitySlug;
                
                if (currentPath.startsWith(`/${currentSlug}/`)) {
                    return currentPath.replace(`/${currentSlug}/`, `/${localitySlug}/`);
                }
                
                return `/${localitySlug}${currentPath}`;
            },
            
            closeModal() {
                this.isModalOpen = false;
            },
            
            openModal() {
                this.isModalOpen = true;
                this.$nextTick(() => {
                    if (this.$refs.searchInput) {
                        this.$refs.searchInput.focus();
                    }
                });
            },
            
            openMobileSelector() {
                this.isMobileSelectorOpen = true;
                this.$nextTick(() => {
                    if (this.$refs.searchInput) {
                        this.$refs.searchInput.focus();
                    }
                });
            },
            
            closePopover() {
                this.isPopoverOpen = false;
            },
            
            confirmLocality() {
                try {
                    localStorage.setItem('selectedLocality', this.currentLocalitySlug);
                    localStorage.setItem('localityConfirmed', 'true');
                    this.closePopover();
                } catch (error) {
                    console.error('Error confirming locality:', error);
                    this.closePopover();
                }
            },
            
            checkLocalityConfirmation() {
                try {
                    const isConfirmed = localStorage.getItem('localityConfirmed') === 'true';
                    const selectedLocality = localStorage.getItem('selectedLocality');
                    
                    if (!selectedLocality || selectedLocality !== this.currentLocalitySlug || !isConfirmed) {
                        this.isPopoverOpen = !isConfirmed || !selectedLocality || selectedLocality !== this.currentLocalitySlug;
                    }
                } catch (error) {
                    console.error('Error checking locality confirmation:', error);
                    this.isPopoverOpen = true;
                }
            },
            
            filteredLocalities() {
                if (!this.debouncedSearch) {
                    return this.localities.sort((a, b) => a.name.localeCompare(b.name));
                }
                
                const query = this.debouncedSearch.toLowerCase();
                return this.localities
                    .filter(locality => locality.name.toLowerCase().includes(query))
                    .sort((a, b) => a.name.localeCompare(b.name));
            },
            
            localitiesWithoutDistrict() {
                return this.filteredLocalities().filter(locality => !locality.district_id);
            },
            
            districts() {
                const districts = [...new Set(this.filteredLocalities()
                    .filter(locality => locality.district_id)
                    .map(locality => locality.district))].sort();
                return districts;
            },
            
            localitiesInSelectedDistrict() {
                if (!this.selectedDistrict) return [];
                return this.filteredLocalities().filter(locality => locality.district === this.selectedDistrict);
            },
            
            initDistrict() {
                const currentLocality = this.localities.find(l => l.slug === this.currentLocalitySlug);
                if (currentLocality?.district_id) {
                    this.selectedDistrict = currentLocality.district;
                }
            },
            
            updateDistrict() {
                const filtered = this.filteredLocalities();
                const firstWithDistrict = filtered.find(locality => locality.district_id);
                this.selectedDistrict = firstWithDistrict ? firstWithDistrict.district : null;
            },
            
            saveSelection(slug) {
                try {
                    localStorage.setItem('selectedLocality', slug);
                    localStorage.setItem('localityConfirmed', 'true');
                    this.isModalOpen = false;
                    this.isMobileSelectorOpen = false;
                    
                    if (slug !== this.currentLocalitySlug) {
                        window.location.href = this.getNewPath(slug);
                    }
                } catch (error) {
                    console.error('Error saving locality selection:', error);
                    if (slug !== this.currentLocalitySlug) {
                        window.location.href = this.getNewPath(slug);
                    }
                }
            },
            
            highlightMatches(name) {
                if (!this.debouncedSearch) return name;
                
                const escapedQuery = this.debouncedSearch.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                const regex = new RegExp(`(${escapedQuery})`, 'gi');
                
                return name.replace(regex, '<strong>$1</strong>');
            },
            
            navigateSuggestions(event) {
                const suggestions = this.filteredLocalities().slice(0, 5);
                if (event.key === 'ArrowDown') {
                    this.highlightedIndex = (this.highlightedIndex === null || this.highlightedIndex >= suggestions.length - 1) ? 0 : this.highlightedIndex + 1;
                } else if (event.key === 'ArrowUp') {
                    this.highlightedIndex = (this.highlightedIndex === null || this.highlightedIndex <= 0) ? suggestions.length - 1 : this.highlightedIndex - 1;
                } else if (event.key === 'Enter' && this.highlightedIndex !== null) {
                    const locality = suggestions[this.highlightedIndex];
                    this.saveSelection(locality.slug);
                }
            },
            
            handleKeydown(e) {
                if (e.key === 'Escape') {
                    this.closeModal();
                    this.closePopover();
                }
            },
            
            init() {
                // Получаем данные из script тега
                const dataScript = document.getElementById('navbar-data');
                if (dataScript) {
                    try {
                        const data = JSON.parse(dataScript.textContent);
                        this.currentLocalitySlug = data.locality_slug || '';
                        this.currentLocalityName = data.locality_name || '';
                        this.currentLocalityNamePrepositional = data.locality_name_prepositional || '';
                        this.localities = data.localities || [];
                        
                        console.log('Data loaded:', {
                            slug: this.currentLocalitySlug,
                            name: this.currentLocalityName,
                            localities: this.localities.length
                        });
                    } catch (error) {
                        console.error('Error parsing navbar data:', error);
                        console.log('Raw data:', dataScript.textContent);
                        this.localities = [];
                    }
                } else {
                    console.error('Navbar data script not found');
                }
                
                this.initDistrict();
                this.checkLocalityConfirmation();
                document.addEventListener('keydown', this.handleKeydown.bind(this));
            },
            
            destroy() {
                document.removeEventListener('keydown', this.handleKeydown.bind(this));
            }
        };
    });
});