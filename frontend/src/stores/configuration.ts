import { defineStore } from 'pinia'

import {
  createAttributeDefinitionApi,
  createAttributeOptionApi,
  createCategoryApi,
  createFamilyMemberApi,
  createItemStatusApi,
  createLocationNodeApi,
  createResidenceApi,
  deleteFamilyMemberApi,
  deleteLocationNodeApi,
  deleteResidenceApi,
  fetchConfigBootstrapApi,
  updateAttributeDefinitionApi,
  updateAttributeOptionApi,
  updateCategoryApi,
  updateDictionaryOptionApi,
  updateFamilyMemberApi,
  updateItemStatusApi,
  updateLocationNodeApi,
  updateResidenceApi,
  uploadResidenceImageApi,
  type AttributeDefinitionCreate,
  type AttributeDefinitionUpdate,
  type AttributeOptionCreate,
  type AttributeOptionUpdate,
  type CategoryCreate,
  type CategoryUpdate,
  type ConfigBootstrap,
  type DictionaryOptionUpdate,
  type FamilyMemberCreate,
  type FamilyMemberUpdate,
  type ItemStatusCreate,
  type ItemStatusUpdate,
  type LocationNodeCreate,
  type LocationNodeUpdate,
  type ResidenceCreate,
  type ResidenceUpdate
} from '../api/configuration'

interface ConfigurationState {
  data: ConfigBootstrap | null
  loading: boolean
}

export const useConfigurationStore = defineStore('configuration', {
  state: (): ConfigurationState => ({ data: null, loading: false }),
  actions: {
    async load() {
      this.loading = true
      try {
        this.data = await fetchConfigBootstrapApi()
      } finally {
        this.loading = false
      }
    },
    async createResidence(payload: ResidenceCreate) {
      const residence = await createResidenceApi(payload)
      await this.load()
      return residence
    },
    async updateResidence(residenceId: number, payload: ResidenceUpdate) {
      const residence = await updateResidenceApi(residenceId, payload)
      await this.load()
      return residence
    },
    async deleteResidence(residenceId: number) {
      const residence = await deleteResidenceApi(residenceId)
      await this.load()
      return residence
    },
    async uploadResidenceImage(residenceId: number, file: File) {
      const residence = await uploadResidenceImageApi(residenceId, file)
      await this.load()
      return residence
    },
    async createLocationNode(payload: LocationNodeCreate) {
      await createLocationNodeApi(payload)
      await this.load()
    },
    async updateLocationNode(nodeId: number, payload: LocationNodeUpdate) {
      await updateLocationNodeApi(nodeId, payload)
      await this.load()
    },
    async deleteLocationNode(nodeId: number) {
      const location = await deleteLocationNodeApi(nodeId)
      await this.load()
      return location
    },
    async createFamilyMember(payload: FamilyMemberCreate) {
      await createFamilyMemberApi(payload)
      await this.load()
    },
    async updateFamilyMember(memberId: number, payload: FamilyMemberUpdate) {
      await updateFamilyMemberApi(memberId, payload)
      await this.load()
    },
    async deleteFamilyMember(memberId: number) {
      const member = await deleteFamilyMemberApi(memberId)
      await this.load()
      return member
    },
    async createCategory(payload: CategoryCreate) {
      await createCategoryApi(payload)
      await this.load()
    },
    async updateCategory(categoryId: number, payload: CategoryUpdate) {
      await updateCategoryApi(categoryId, payload)
      await this.load()
    },
    async createAttributeDefinition(payload: AttributeDefinitionCreate) {
      await createAttributeDefinitionApi(payload)
      await this.load()
    },
    async updateAttributeDefinition(definitionId: number, payload: AttributeDefinitionUpdate) {
      await updateAttributeDefinitionApi(definitionId, payload)
      await this.load()
    },
    async createAttributeOption(payload: AttributeOptionCreate) {
      await createAttributeOptionApi(payload)
      await this.load()
    },
    async updateAttributeOption(optionId: number, payload: AttributeOptionUpdate) {
      await updateAttributeOptionApi(optionId, payload)
      await this.load()
    },
    async updateDictionaryOption(optionId: number, payload: DictionaryOptionUpdate) {
      await updateDictionaryOptionApi(optionId, payload)
      await this.load()
    },
    async createItemStatus(payload: ItemStatusCreate) {
      await createItemStatusApi(payload)
      await this.load()
    },
    async updateItemStatus(statusId: number, payload: ItemStatusUpdate) {
      await updateItemStatusApi(statusId, payload)
      await this.load()
    }
  }
})
